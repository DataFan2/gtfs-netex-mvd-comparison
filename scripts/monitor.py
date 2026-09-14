#!/usr/bin/env python3
"""
GTFS-NeTEx comparability monitor.

Resolves the newest published GTFS and NeTEx release for each configured country,
downloads both, and computes Minimum Viable Denominator coverage for stops and routes.
Appends one record per country to docs/results/<country>.json.

Method follows Miclaus & Sohi, "It is Not the Standard, It is the Feed" (Sem4Tra 2026).

Two rates are reported per dimension. The GTFS-side rate is matched units against the
GTFS total, the NeTEx-side rate against the NeTEx total. A smaller feed can be fully
contained in a larger one without the two disagreeing, and a single symmetric score
would hide that.

Usage:
    python scripts/monitor.py              # every country
    python scripts/monitor.py luxembourg   # one country
"""
import csv
import datetime
import io
import json
import math
import pathlib
import re
import sys
import time
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "docs" / "results"
UA = {"User-Agent": "mvd-monitor/2.0 (+https://github.com/DataFan2/gtfs-netex-mvd-comparison)"}


# --------------------------------------------------------------------------- io

def fetch(url, timeout=600):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def head(url, timeout=60):
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        # Header names are case-insensitive on the wire; normalise so lookups are stable.
        return {k.lower(): v for k, v in r.headers.items()}


def fetch_file(url, path, timeout=900, attempts=5):
    """
    Stream a download to disk, verifying the length and resuming if it is cut short.

    Some national feeds are several hundred megabytes and the connection does drop.
    A silently truncated zip looks valid until it is opened, so the size is checked
    against Content-Length and the transfer is resumed with a Range request.
    """
    path = pathlib.Path(path)
    expected = None
    try:
        expected = int(head(url, timeout=60).get("content-length", 0)) or None
    except Exception:
        pass

    for attempt in range(attempts):
        have = path.stat().st_size if path.exists() else 0
        if expected and have == expected:
            return path
        headers = dict(UA)
        if have and expected:
            headers["Range"] = f"bytes={have}-"
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=headers), timeout=timeout) as r, \
                 open(path, "ab" if headers.get("Range") else "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
        except Exception as e:
            print(f"    download attempt {attempt + 1} failed: {type(e).__name__}", flush=True)
        if expected is None:
            return path

    have = path.stat().st_size if path.exists() else 0
    if expected and have != expected:
        raise RuntimeError(f"incomplete download: {have} of {expected} bytes from {url}")
    return path


def gtfs_table(source, name):
    """Read one GTFS table from a zip, given either its bytes or a path on disk."""
    handle = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else str(source)
    with zipfile.ZipFile(handle) as z:
        names = z.namelist()
        target = name if name in names else next(
            (n for n in names if n.lower().endswith("/" + name)), None)
        if target is None:
            raise FileNotFoundError(name)
        with z.open(target) as f:
            return list(csv.DictReader(io.TextIOWrapper(f, "utf-8-sig")))


# ------------------------------------------------------------------ netex scan

RE_STOPPLACE_BLOCK = re.compile(rb'<StopPlace id="([^"]+)".*?</StopPlace>', re.S)
RE_STOPPLACE_ID = re.compile(rb'<StopPlace\b[^>]*\bid="([^"]+)"')
RE_LON = re.compile(rb'<Longitude>([-\d.]+)</Longitude>')
RE_LAT = re.compile(rb'<Latitude>([-\d.]+)</Latitude>')
RE_LINE_ID = re.compile(rb'<Line id="([^"]+)"')
RE_LINE_BLOCK = re.compile(rb"<Line\b[^>]*>(.*?)</Line>", re.S)
RE_PUBCODE = re.compile(rb"<PublicCode>([^<]*)</PublicCode>")


def netex_members(zbytes):
    """Yield (name, opener) for every XML member of a NeTEx zip."""
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    for name in z.namelist():
        if name.lower().endswith(".xml"):
            yield name, (lambda n=name: z.open(n))


def scan_stopplaces_and_lines(zbytes, want_coords):
    """
    Stream every XML member and collect StopPlace and Line records.

    Returns (stopplaces, line_ids, line_codes) where stopplaces is a list of
    (id, lat, lon) when want_coords is true, otherwise a list of (id, None, None).

    Streamed in chunks with an overlap, because some national NeTEx files are
    several hundred megabytes uncompressed.
    """
    # Keyed by id, because the chunk overlap below can present the same record twice.
    stopplaces_by_id, line_ids, line_codes = {}, set(), set()
    OVERLAP = 200_000
    for _, opener in netex_members(zbytes):
        with opener() as f:
            tail = b""
            while True:
                chunk = f.read(8 << 20)
                if not chunk:
                    break
                buf = tail + chunk
                if want_coords:
                    for m in RE_STOPPLACE_BLOCK.finditer(buf):
                        blk = m.group(0)
                        lo, la = RE_LON.search(blk), RE_LAT.search(blk)
                        if lo and la:
                            sid = m.group(1).decode()
                            stopplaces_by_id[sid] = (sid, float(la.group(1)), float(lo.group(1)))
                else:
                    for m in RE_STOPPLACE_ID.finditer(buf):
                        sid = m.group(1).decode()
                        stopplaces_by_id[sid] = (sid, None, None)
                for m in RE_LINE_ID.finditer(buf):
                    line_ids.add(m.group(1).decode())
                for m in RE_LINE_BLOCK.finditer(buf):
                    pc = RE_PUBCODE.search(m.group(1))
                    if pc and pc.group(1).strip():
                        line_codes.add(pc.group(1).decode().strip().upper())
                tail = buf[-OVERLAP:]
    return list(stopplaces_by_id.values()), line_ids, line_codes


# --------------------------------------------------------------------- geometry

def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres."""
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def match_by_distance(gtfs_points, netex_points, threshold_m):
    """
    Nearest-neighbour match within a distance threshold, many-to-one.

    gtfs_points  : list of (lat, lon)
    netex_points : list of (id, lat, lon)

    Returns (matched_gtfs_count, distinct_netex_matched).
    """
    CELL = 0.01
    grid = {}
    for sid, la, lo in netex_points:
        grid.setdefault((int(la / CELL), int(lo / CELL)), []).append((sid, la, lo))

    matched, used = 0, set()
    for la, lo in gtfs_points:
        best, bestd = None, float("inf")
        ci, cj = int(la / CELL), int(lo / CELL)
        for i in (ci - 1, ci, ci + 1):
            for j in (cj - 1, cj, cj + 1):
                for sid, sla, slo in grid.get((i, j), ()):
                    d = haversine(la, lo, sla, slo)
                    if d < bestd:
                        best, bestd = sid, d
        if best is not None and bestd <= threshold_m:
            matched += 1
            used.add(best)
    return matched, len(used)


def rates(matched, gtfs_total, netex_total):
    return {
        "matched": matched,
        "gtfs": gtfs_total,
        "netex": netex_total,
        "gtfs_pct": round(matched / gtfs_total * 100, 2) if gtfs_total else 0.0,
        "netex_pct": round(matched / netex_total * 100, 2) if netex_total else 0.0,
    }



# --------------------------------------------------------------------- calendars
#
# The calendar rule is the one from Calendar_Unified_Method/calendar_comparison.py.
# Each calendar is reduced to its day-by-day activity pattern inside the window the
# two feeds share, and two calendars match only if those patterns are identical.
# Patterns are compared as distinct sets, not per service id, because many services
# share one calendar and the two formats group them differently.

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

RE_DTA = re.compile(rb'<DayTypeAssignment\b[^>]*\bid="([^"]+)"(.*?)</DayTypeAssignment>', re.S)
RE_OPREF = re.compile(rb'<OperatingPeriodRef\b[^>]*\bref="([^"]+)"')
RE_UIC = re.compile(rb'<UicOperatingPeriod\b[^>]*\bid="([^"]+)"(.*?)</UicOperatingPeriod>', re.S)
RE_FROMDATE = re.compile(rb"<FromDate>([\d-]{10})")
RE_VALIDBITS = re.compile(rb"<ValidDayBits>([01]+)</ValidDayBits>")


def _ymd(s):
    return datetime.date(int(s[0:4]), int(s[4:6]), int(s[6:8]))


def gtfs_active_dates(source):
    """
    {service_id: set of active dates} from calendar.txt and calendar_dates.txt.

    Feeds that publish no weekday rule, and express validity only as explicit
    added dates, are handled by the second loop.
    """
    try:
        cal = gtfs_table(source, "calendar.txt")
    except FileNotFoundError:
        cal = []
    try:
        exc = gtfs_table(source, "calendar_dates.txt")
    except FileNotFoundError:
        exc = []

    added, removed = {}, {}
    for r in exc:
        d = _ymd(r["date"])
        if int(r["exception_type"]) == 1:
            added.setdefault(r["service_id"], set()).add(d)
        else:
            removed.setdefault(r["service_id"], set()).add(d)

    out = {}
    for r in cal:
        sid = r["service_id"]
        start, end = _ymd(r["start_date"]), _ymd(r["end_date"])
        on = [i for i, c in enumerate(WEEKDAYS) if r.get(c) == "1"]
        active, d = set(), start
        while d <= end:
            if d.weekday() in on:
                active.add(d)
            d += datetime.timedelta(days=1)
        active -= removed.get(sid, set())
        active |= added.get(sid, set())
        if active:
            out[sid] = active

    for sid, dates in added.items():
        out.setdefault(sid, set(dates))
    return out


def _uic_periods(buf):
    """{UicOperatingPeriod id: (from date, bit string)} found in one buffer."""
    found = {}
    for m in RE_UIC.finditer(buf):
        fd, bits = RE_FROMDATE.search(m.group(2)), RE_VALIDBITS.search(m.group(2))
        if fd and bits:
            found[m.group(1).decode()] = (fd.group(1).decode(), bits.group(1).decode())
    return found


def _bits_to_dates(from_date, bits):
    d0 = datetime.date.fromisoformat(from_date)
    return {d0 + datetime.timedelta(days=i) for i, b in enumerate(bits) if b == "1"}


def netex_dates_via_assignment(buffers):
    """DayTypeAssignment -> UicOperatingPeriod, keyed by assignment id."""
    assignments, periods = {}, {}
    for buf in buffers:
        for m in RE_DTA.finditer(buf):
            ref = RE_OPREF.search(m.group(2))
            if ref:
                assignments[m.group(1).decode()] = ref.group(1).decode()
        periods.update(_uic_periods(buf))
    out = {}
    for aid, ref in assignments.items():
        p = periods.get(ref)
        if p:
            dates = _bits_to_dates(*p)
            if dates:
                out[aid] = dates
    return out


def netex_dates_direct(buffers):
    """UicOperatingPeriod on its own, keyed by its own id, with no assignment join."""
    out = {}
    for buf in buffers:
        for pid, p in _uic_periods(buf).items():
            dates = _bits_to_dates(*p)
            if dates:
                out[pid] = dates
    return out


def calendar_rates(gtfs_dates_by_id, netex_dates_by_id):
    g_all = [d for s in gtfs_dates_by_id.values() for d in s]
    n_all = [d for s in netex_dates_by_id.values() for d in s]
    if not g_all or not n_all:
        return {"available": False, "note": "no calendar data could be extracted"}
    start, end = max(min(g_all), min(n_all)), min(max(g_all), max(n_all))
    if end < start:
        return {"available": False, "note": "the two feeds share no common validity window"}
    days = (end - start).days + 1

    def distinct_patterns(dates_by_id):
        tuples = set()
        for dates in dates_by_id.values():
            offs = tuple(sorted({(d - start).days for d in dates if start <= d <= end}))
            if offs:
                tuples.add(offs)
        out = set()
        for offs in tuples:
            bits = bytearray(b"0" * days)
            for o in offs:
                bits[o] = 49  # ord("1")
            out.add(bytes(bits))
        return out

    gp, np_ = distinct_patterns(gtfs_dates_by_id), distinct_patterns(netex_dates_by_id)
    rec = rates(len(gp & np_), len(gp), len(np_))
    rec["window_days"] = days
    rec["window_from"] = start.isoformat()
    rec["window_to"] = end.isoformat()
    return rec



# DayType + DayTypeAssignment + OperatingPeriod is the third shape DATA4PT documents
# for a GTFS calendar. There is no ready-made bit string, so the active days are
# rebuilt from a weekday rule applied across a date range, plus single-date exceptions.

DOW = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
       "friday": 4, "saturday": 5, "sunday": 6}

RE_DAYTYPE = re.compile(rb'<DayType\b[^>]*\bid="([^"]+)"(.*?)</DayType>', re.S)
RE_DAYSOFWEEK = re.compile(rb"<DaysOfWeek>([^<]*)</DaysOfWeek>")
RE_OPERPERIOD = re.compile(rb'<OperatingPeriod\b[^>]*\bid="([^"]+)"(.*?)</OperatingPeriod>', re.S)
RE_TODATE = re.compile(rb"<ToDate>(\d{4}-\d{2}-\d{2})")
RE_FROMDATE10 = re.compile(rb"<FromDate>(\d{4}-\d{2}-\d{2})")
RE_DTA_BODY = re.compile(rb"<DayTypeAssignment\b[^>]*>(.*?)</DayTypeAssignment>", re.S)
RE_DAYTYPEREF = re.compile(rb'<DayTypeRef\b[^>]*\bref="([^"]+)"')
RE_SINGLEDATE = re.compile(rb"<Date>(\d{4}-\d{2}-\d{2})")
RE_ISAVAILABLE = re.compile(rb"<isAvailable>(\w+)</isAvailable>")


def _days_of_week(text):
    out = set()
    for token in re.split(r"[\s,]+", text.strip()):
        t = token.lower()
        if t in DOW:
            out.add(DOW[t])
        elif t == "weekdays":
            out |= {0, 1, 2, 3, 4}
        elif t in ("weekend", "weekends"):
            out |= {5, 6}
        elif t == "everyday":
            out |= set(range(7))
    return out


def netex_dates_via_daytype(buffers):
    """{DayType id: set of active dates} for feeds using the weekday-rule shape."""
    daytypes, periods, assignments = {}, {}, []
    for buf in buffers:
        for m in RE_DAYTYPE.finditer(buf):
            dows = set()
            for x in RE_DAYSOFWEEK.finditer(m.group(2)):
                dows |= _days_of_week(x.group(1).decode())
            daytypes[m.group(1).decode()] = dows
        for m in RE_OPERPERIOD.finditer(buf):
            f, t = RE_FROMDATE10.search(m.group(2)), RE_TODATE.search(m.group(2))
            if f and t:
                periods[m.group(1).decode()] = (f.group(1).decode(), t.group(1).decode())
        for m in RE_DTA_BODY.finditer(buf):
            body = m.group(1)
            ref = RE_DAYTYPEREF.search(body)
            if ref:
                assignments.append((ref.group(1).decode(),
                                    RE_OPREF.search(body),
                                    RE_SINGLEDATE.search(body),
                                    RE_ISAVAILABLE.search(body)))

    added, removed = {}, {}
    for dt_ref, period_ref, single_date, available in assignments:
        dows = daytypes.get(dt_ref, set())
        if period_ref is not None:
            p = periods.get(period_ref.group(1).decode())
            if not p:
                continue
            d = datetime.date.fromisoformat(p[0])
            last = datetime.date.fromisoformat(p[1])
            target = added.setdefault(dt_ref, set())
            while d <= last:
                if not dows or d.weekday() in dows:
                    target.add(d)
                d += datetime.timedelta(days=1)
        elif single_date is not None:
            d = datetime.date.fromisoformat(single_date.group(1).decode())
            keep = available is None or available.group(1).decode().lower() == "true"
            (added if keep else removed).setdefault(dt_ref, set()).add(d)

    out = {}
    for key, dates in added.items():
        dates = dates - removed.get(key, set())
        if dates:
            out[key] = dates
    return out


def netex_xml_buffers(zip_path_or_bytes, member_filter=None):
    """Read NeTEx XML members into memory, optionally only those matching a filter."""
    handle = io.BytesIO(zip_path_or_bytes) if isinstance(zip_path_or_bytes, (bytes, bytearray)) \
        else str(zip_path_or_bytes)
    with zipfile.ZipFile(handle) as z:
        for name in z.namelist():
            if not name.lower().endswith(".xml"):
                continue
            if member_filter and not member_filter(name):
                continue
            yield z.read(name)


# =========================================================================
# Luxembourg
# =========================================================================

LU_API = "https://data.public.lu/api/1/datasets/{}/"
LU_SETS = {
    "gtfs": "horaires-et-arrets-des-transport-publics-gtfs",
    "netex": "horaires-et-arrets-des-transport-publics-netex",
}


def lu_newest(slug):
    data = json.loads(fetch(LU_API.format(slug), timeout=60))
    best = None
    for r in data["resources"]:
        t = r.get("title", "")
        if not t.lower().endswith(".zip"):
            continue
        m = re.search(r"(\d{8})-(\d{8})", t)
        if not m:
            continue
        if best is None or m.group(1) > best[0]:
            best = (m.group(1), t, r["url"])
    if best is None:
        raise RuntimeError(f"no dated zip resource for {slug}")
    return {"valid_from": best[0], "file": best[1], "url": best[2]}


def run_luxembourg():
    g, n = lu_newest(LU_SETS["gtfs"]), lu_newest(LU_SETS["netex"])
    gtfs_bytes, netex_bytes = fetch(g["url"]), fetch(n["url"])

    def core(v):
        v = (v or "").strip().lstrip("0")
        return v if v.isdigit() else None

    gtfs_stop_ids = {c for c in (core(r["stop_id"])
                                 for r in gtfs_table(gtfs_bytes, "stops.txt")) if c}
    sp, _, line_codes = scan_stopplaces_and_lines(netex_bytes, want_coords=False)
    nx_stop_ids = set()
    for sid, _, _ in sp:
        m = re.search(r":(\d+)_", sid)
        if m:
            nx_stop_ids.add(m.group(1).lstrip("0"))

    gtfs_routes = {r["route_short_name"].strip().upper()
                   for r in gtfs_table(gtfs_bytes, "routes.txt")
                   if r["route_short_name"].strip()}

    calendars = calendar_rates(
        gtfs_active_dates(gtfs_bytes),
        netex_dates_via_assignment(netex_xml_buffers(netex_bytes)))

    return {
        "country": "Luxembourg",
        "code": "LU",
        "method": {"stops": "shared identifier", "routes": "public line label",
                   "calendars": "day-by-day activity pattern"},
        "release": {"gtfs": {"file": g["file"], "valid_from": g["valid_from"]},
                    "netex": {"file": n["file"], "valid_from": n["valid_from"]}},
        "stops": rates(len(gtfs_stop_ids & nx_stop_ids), len(gtfs_stop_ids), len(nx_stop_ids)),
        "routes": rates(len(gtfs_routes & line_codes), len(gtfs_routes), len(line_codes)),
        "calendars": calendars,
    }


# =========================================================================
# France
# =========================================================================

FR_GTFS = "https://eu.ftp.opendatasoft.com/sncf/plandata/Export_OpenData_SNCF_GTFS_NewTripId.zip"
FR_NETEX = "https://eu.ftp.opendatasoft.com/sncf/plandata/export-opendata-sncf-netex.zip"
FR_THRESHOLD_M = 50


def run_france():
    g_head, n_head = head(FR_GTFS), head(FR_NETEX)
    gtfs_bytes, netex_bytes = fetch(FR_GTFS), fetch(FR_NETEX)

    stations = [r for r in gtfs_table(gtfs_bytes, "stops.txt") if r["location_type"] == "1"]
    gtfs_points = [(float(r["stop_lat"]), float(r["stop_lon"])) for r in stations]
    gtfs_routes = {r["route_id"] for r in gtfs_table(gtfs_bytes, "routes.txt")}

    sp, line_ids, _ = scan_stopplaces_and_lines(netex_bytes, want_coords=True)
    matched, netex_used = match_by_distance(gtfs_points, sp, FR_THRESHOLD_M)

    stops = rates(matched, len(gtfs_points), len(sp))
    stops["netex_pct"] = round(netex_used / len(sp) * 100, 2) if sp else 0.0
    stops["netex_matched_distinct"] = netex_used

    calendars = calendar_rates(
        gtfs_active_dates(gtfs_bytes),
        netex_dates_direct(netex_xml_buffers(netex_bytes)))

    return {
        "country": "France",
        "code": "FR",
        "method": {"stops": f"coordinates, {FR_THRESHOLD_M} m", "routes": "shared identifier",
                   "calendars": "day-by-day activity pattern"},
        "release": {"gtfs": {"file": FR_GTFS.rsplit("/", 1)[-1],
                             "published": g_head.get("last-modified")},
                    "netex": {"file": FR_NETEX.rsplit("/", 1)[-1],
                              "published": n_head.get("last-modified")}},
        "stops": stops,
        "routes": rates(len(gtfs_routes & line_ids), len(gtfs_routes), len(line_ids)),
        "calendars": calendars,
    }


# =========================================================================

# =========================================================================
# Netherlands
# =========================================================================

NL_GTFS = "https://gtfs.ovapi.nl/nl/gtfs-nl.zip"
NL_NETEX_DIR = "https://data.ndovloket.nl/netex/epiap/"
NL_THRESHOLD_M = 50

RE_SP_NL = re.compile(rb'<StopPlace id="([^"]+)".*?</StopPlace>', re.S)
RE_GMLPOS = re.compile(rb"<gml:pos>([-\d.]+)\s+([-\d.]+)</gml:pos>")


def nl_newest_netex():
    """The NeTEx directory listing carries one dated file per publication."""
    html = fetch(NL_NETEX_DIR, timeout=60).decode("utf-8", "replace")
    files = re.findall(r'href="(NeTEx_DOVA_epiap_(\d{4}-\d{2}-\d{2})\.xml\.gz)"', html)
    if not files:
        raise RuntimeError("no dated NeTEx file found in the Dutch listing")
    name, date = max(files, key=lambda t: t[1])
    return {"file": name, "valid_from": date.replace("-", ""), "url": NL_NETEX_DIR + name}


def run_netherlands():
    import gzip
    from pyproj import Transformer

    n = nl_newest_netex()
    g_head = head(NL_GTFS)

    tmp = ROOT / "_tmp_nl_gtfs.zip"
    try:
        fetch_file(NL_GTFS, tmp)
        stations = [r for r in gtfs_table(tmp, "stops.txt") if r["location_type"] == "1"]
        gtfs_points = [(float(r["stop_lat"]), float(r["stop_lon"])) for r in stations]
    finally:
        tmp.unlink(missing_ok=True)

    xml = gzip.decompress(fetch(n["url"]))

    # Dutch NeTEx stores positions in RD New (EPSG:28992), not in latitude/longitude.
    to_wgs84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    netex_points, line_ids = [], set()
    for m in RE_SP_NL.finditer(xml):
        pos = RE_GMLPOS.search(m.group(0))
        if not pos:
            continue
        lon, lat = to_wgs84.transform(float(pos.group(1)), float(pos.group(2)))
        netex_points.append((m.group(1).decode(), lat, lon))
    for m in RE_LINE_ID.finditer(xml):
        line_ids.add(m.group(1).decode())

    matched, netex_used = match_by_distance(gtfs_points, netex_points, NL_THRESHOLD_M)
    stops = rates(matched, len(gtfs_points), len(netex_points))
    stops["netex_pct"] = round(netex_used / len(netex_points) * 100, 2) if netex_points else 0.0
    stops["netex_matched_distinct"] = netex_used

    routes = {"available": False,
              "note": "the Dutch NeTEx feed contains no Line elements, so routes cannot be compared"}

    return {
        "country": "Netherlands",
        "code": "NL",
        "method": {"stops": f"coordinates, {NL_THRESHOLD_M} m", "routes": "not comparable"},
        "release": {"gtfs": {"file": NL_GTFS.rsplit("/", 1)[-1],
                             "published": g_head.get("last-modified")},
                    "netex": {"file": n["file"], "valid_from": n["valid_from"]}},
        "stops": stops,
        "routes": routes,
        "calendars": {"available": False,
                      "note": "calendar extraction for this feed is not implemented yet"},
    }


# =========================================================================
# Switzerland
# =========================================================================

CH_GTFS_PAGE = "https://data.opentransportdata.swiss/dataset/timetable-2026-gtfs2020"
CH_NETEX_PAGE = "https://data.opentransportdata.swiss/dataset/timetablenetex_2026"
CH_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36"}

RE_ZIP_URL = re.compile(r'https?://[^"\']+?\.zip')


def ch_newest(page_url, filename_pattern):
    """Pick the newest dated zip linked from an opentransportdata.swiss dataset page."""
    html = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(page_url, headers=CH_UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                html = r.read().decode("utf-8", "replace")
            break
        except Exception as e:
            print(f"    dataset page attempt {attempt + 1} failed: {type(e).__name__}", flush=True)
            time.sleep(3)
    if html is None:
        raise RuntimeError(f"could not read {page_url}")
    best = None
    for url in set(RE_ZIP_URL.findall(html)):
        fname = url.rsplit("/", 1)[-1]
        m = re.search(filename_pattern, fname)
        if not m:
            continue
        key = m.group(1).replace("-", "")[:8]
        if best is None or key > best["valid_from"]:
            best = {"valid_from": key, "file": fname, "url": url}
    if best is None:
        raise RuntimeError(f"no dated zip found on {page_url}")
    return best


def ch_core(value):
    """Swiss station number: strip the GTFS Parent prefix, then take the trailing digits."""
    s = str(value).strip()
    if s.startswith("Parent"):
        s = s[len("Parent"):]
    m = re.search(r"(\d+)$", s)
    return m.group(1) if m else s


def run_switzerland():
    g = ch_newest(CH_GTFS_PAGE, r"gtfs_fp\d{4}_(\d{4}-?\d{2}-?\d{2})")
    n = ch_newest(CH_NETEX_PAGE, r"_1_1_(\d{12})")

    gtfs_path = ROOT / "_tmp_ch_gtfs.zip"
    netex_path = ROOT / "_tmp_ch_netex.zip"
    try:
        fetch_file(g["url"], gtfs_path)
        fetch_file(n["url"], netex_path)

        stations = [r for r in gtfs_table(gtfs_path, "stops.txt") if r["location_type"] == "1"]
        # The Swiss GTFS carries the national DiDok station number in its own column.
        # The stop_id itself moved to an internal sloid scheme, which does not join.
        gtfs_ids = {(r.get("didok") or "").strip()
                    for r in stations if (r.get("didok") or "").strip()}
        gtfs_labels = {re.sub(r"\s+", "", r["route_short_name"].strip().upper())
                       for r in gtfs_table(gtfs_path, "routes.txt")
                       if r["route_short_name"].strip()}

        # Only two of the 438 NeTEx members carry stop places and lines. The archive
        # is about 31 GB uncompressed, so the rest is deliberately not opened.
        with zipfile.ZipFile(netex_path) as z:
            site = next(m for m in z.namelist() if "_SITE_" in m)
            service = next(m for m in z.namelist()
                           if "_SERVICE_" in m and "CALENDAR" not in m)
            site_xml = z.read(site)
            service_xml = z.read(service)
    finally:
        gtfs_path.unlink(missing_ok=True)
        netex_path.unlink(missing_ok=True)

    netex_ids = {ch_core(x.decode())
                 for x in RE_STOPPLACE_ID.findall(site_xml)}
    netex_labels = set()
    for m in RE_LINE_BLOCK.finditer(service_xml):
        pc = RE_PUBCODE.search(m.group(1))
        if pc and pc.group(1).strip():
            netex_labels.add(re.sub(r"\s+", "", pc.group(1).decode().strip().upper()))

    return {
        "country": "Switzerland",
        "code": "CH",
        "method": {"stops": "shared identifier (DiDok station number)",
                   "routes": "public line label"},
        "release": {"gtfs": {"file": g["file"], "valid_from": g["valid_from"]},
                    "netex": {"file": n["file"], "valid_from": n["valid_from"]}},
        "stops": rates(len(gtfs_ids & netex_ids), len(gtfs_ids), len(netex_ids)),
        "routes": rates(len(gtfs_labels & netex_labels), len(gtfs_labels), len(netex_labels)),
        "calendars": {"available": False,
                      "note": "calendar extraction for this feed is not implemented yet"},
    }


# =========================================================================
# Norway
# =========================================================================

NO_GTFS = "https://storage.googleapis.com/marduk-production/outbound/gtfs/rb_norway-aggregated-gtfs.zip"
NO_NETEX = "https://storage.googleapis.com/marduk-production/outbound/netex/rb_norway-aggregated-netex.zip"

RE_LINE_BLOCK_ID = re.compile(rb'<Line\b[^>]*\bid="([^"]+)"(.*?)</Line>', re.S)


def run_norway():
    g_head, n_head = head(NO_GTFS), head(NO_NETEX)
    gtfs_path = ROOT / "_tmp_no_gtfs.zip"
    netex_path = ROOT / "_tmp_no_netex.zip"
    try:
        fetch_file(NO_GTFS, gtfs_path)
        fetch_file(NO_NETEX, netex_path)

        stations = [r for r in gtfs_table(gtfs_path, "stops.txt")
                    if r["location_type"] == "1"]
        gtfs_ids = {r["stop_id"].strip() for r in stations}
        gtfs_labels = {re.sub(r"\s+", "", r["route_short_name"].strip().upper())
                       for r in gtfs_table(gtfs_path, "routes.txt")
                       if r["route_short_name"].strip()}

        netex_ids, netex_labels = set(), set()
        with zipfile.ZipFile(netex_path) as z:
            # Every stop place lives in one member. The rest of the archive is the
            # timetable, about 5 GB uncompressed, and is not needed here.
            stops_member = next(m for m in z.namelist() if m.endswith("_stops.xml"))
            with z.open(stops_member) as f:
                tail = b""
                while True:
                    chunk = f.read(8 << 20)
                    if not chunk:
                        break
                    buf = tail + chunk
                    netex_ids |= {x.decode() for x in RE_STOPPLACE_ID.findall(buf)}
                    tail = buf[-4096:]

            # Lines are published one per file. The Line element sits near the top of
            # each, so only the opening portion of every file is read.
            for member in z.namelist():
                if "-Line-" not in member or not member.endswith(".xml"):
                    continue
                buf = b""
                with z.open(member) as f:
                    while len(buf) < (4 << 20):
                        chunk = f.read(512 << 10)
                        if not chunk:
                            break
                        buf += chunk
                        if b"</Line>" in buf:
                            break
                m = RE_LINE_BLOCK_ID.search(buf)
                if not m:
                    continue
                pc = RE_PUBCODE.search(m.group(2))
                if pc and pc.group(1).strip():
                    netex_labels.add(re.sub(r"\s+", "", pc.group(1).decode().strip().upper()))

            shared = [z.read(m) for m in z.namelist() if "shared_data" in m]

        # The Norwegian calendar shape (weekday rule over a date range) is implemented
        # but not yet validated against the per-country notebook, so it is withheld.
        calendars = {"available": False,
                     "note": "calendar extraction for this feed is implemented but not yet validated"}
        _unvalidated = calendar_rates(gtfs_active_dates(gtfs_path),
                                      netex_dates_via_daytype(shared))  # noqa: F841
    finally:
        gtfs_path.unlink(missing_ok=True)
        netex_path.unlink(missing_ok=True)

    return {
        "country": "Norway",
        "code": "NO",
        "method": {"stops": "shared identifier (NSR)", "routes": "public line label",
                   "calendars": "day-by-day activity pattern"},
        "release": {"gtfs": {"file": NO_GTFS.rsplit("/", 1)[-1],
                             "published": g_head.get("last-modified")},
                    "netex": {"file": NO_NETEX.rsplit("/", 1)[-1],
                              "published": n_head.get("last-modified")}},
        "stops": rates(len(gtfs_ids & netex_ids), len(gtfs_ids), len(netex_ids)),
        "routes": rates(len(gtfs_labels & netex_labels), len(gtfs_labels), len(netex_labels)),
        "calendars": calendars,
    }


# =========================================================================

COUNTRIES = {
    "luxembourg": run_luxembourg,
    "france": run_france,
    "switzerland": run_switzerland,
    "norway": run_norway,
    "netherlands": run_netherlands,
}


def main(argv):
    wanted = [a.lower() for a in argv[1:]] or list(COUNTRIES)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    failures = []

    for key in wanted:
        if key not in COUNTRIES:
            print(f"unknown country: {key}", file=sys.stderr)
            failures.append(key)
            continue
        print(f"--- {key} ---", flush=True)
        try:
            rec = COUNTRIES[key]()
        except Exception as e:
            print(f"    failed: {type(e).__name__}: {e}", file=sys.stderr)
            failures.append(key)
            continue

        rec["checked"] = datetime.datetime.now(datetime.timezone.utc)\
                                  .strftime("%Y-%m-%dT%H:%M:%SZ")
        path = OUTDIR / f"{key}.json"
        history = json.loads(path.read_text()) if path.exists() else []
        history.append(rec)
        path.write_text(json.dumps(history, indent=2) + "\n")

        for label in ("stops", "routes", "calendars"):
            d = rec[label]
            if d.get("available") is False:
                print(f"    {label:<6} not comparable: {d['note']}")
            else:
                print(f"    {label:<6} {d['matched']:>7,} / {d['gtfs']:,} GTFS / {d['netex']:,} NeTEx"
                      f"   {d['gtfs_pct']}% / {d['netex_pct']}%")

    index = sorted(p.stem for p in OUTDIR.glob("*.json") if p.stem != "index")
    (OUTDIR / "index.json").write_text(json.dumps(index, indent=2) + "\n")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
