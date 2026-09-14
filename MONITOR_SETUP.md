# Live MVD monitor

A scheduled job that reruns the paper's comparison on whatever the countries are
publishing today. It resolves the newest GTFS and NeTEx release for each country,
downloads both, recomputes Minimum Viable Denominator coverage, and appends the
result to a JSON file that a web page reads.

## Countries covered

| Country | Stops | Routes | Calendars |
|---|---|---|---|
| Luxembourg | shared identifier | public line label | day pattern |
| France | coordinates, 50 m | shared identifier | day pattern |
| Switzerland | DiDok station number | public line label | not yet |
| Norway | shared identifier (NSR) | public line label | day pattern |
| Netherlands | coordinates, 50 m | no lines in NeTEx | not yet |

Only countries whose feeds can be downloaded without registration or an API key can
be monitored. Sweden, Germany, Spain and Austria cannot, because their portals
require an account. That constraint, rather than data quality, is what limits the list.

## What is in this package

| Path | Purpose |
|---|---|
| `scripts/monitor.py` | Fetches every feed and computes the figures |
| `.github/workflows/monitor.yml` | Runs the script weekly and commits the result |
| `requirements-monitor.txt` | One dependency, `pyproj`, needed for the Dutch coordinates |
| `docs/index.html` | The dashboard page |
| `docs/results/*.json` | One file per country, one record per run |

## Install into the repository

1. Copy the paths above into the root of the repository, keeping the folder structure.
2. Commit and push.
3. Open **Settings**, then **Pages**. Set **Source** to *Deploy from a branch*, branch
   `main`, folder `/docs`. Save.
4. Open **Settings**, then **Actions**, then **General**. Under *Workflow permissions*
   select **Read and write permissions**. Save. Without this the job cannot commit
   what it computed.
5. Open the **Actions** tab, select *MVD monitor*, and press **Run workflow**.

The page is then live at `https://<username>.github.io/<repository>/`.

## Schedule

Weekly, 04:00 UTC on Mondays, plus a manual button. Most of these countries republish
weekly, so more often than that produces no new information.

A full run moves about 1.5 GB and finishes in two to three minutes.

## Running it locally

```bash
pip install -r requirements-monitor.txt
python scripts/monitor.py                 # every country
python scripts/monitor.py luxembourg      # just one
```

Results are appended to `docs/results/<country>.json`.

## What is computed

**Stops.** Matched on a shared identifier where the two feeds carry one, and otherwise
on coordinates within a fixed distance using the great-circle formula.

**Routes.** Compared either on a shared identifier or at the level of unique public
line labels. Both formats create a separate record for every direction and journey
pattern of the same line, and they do not create the same number of them, so counting
records would measure modelling style rather than agreement.

**Calendars.** Each calendar is reduced to its day-by-day activity pattern inside the
window the two feeds share, one character per day. Two calendars match only when those
patterns are identical. Patterns are compared as distinct sets, not per service id.

**Two rates per dimension.** The GTFS-side rate is matched units against the GTFS
total, the NeTEx-side rate against the NeTEx total. A smaller feed can be fully
contained in a larger one without the two disagreeing, and the direction of the
imbalance is as informative as its size.

## Notes on individual countries

**Switzerland** changed its GTFS `stop_id` scheme in June 2026, two months after the
snapshot used in the paper. Identifiers moved from the DiDok station number to an
internal SLOID. The DiDok number is still published, in its own column, and that is
what the monitor joins on. A join built on the old field would now return about 27
per cent.

**Netherlands** publishes NeTEx with no `Line` elements at all, so the route dimension
is reported as not comparable rather than as zero. Its coordinates are in RD New
(EPSG:28992) and are converted to WGS84 before matching.

**Norway** publishes NeTEx as roughly 4,800 files, about 5 GB uncompressed. The monitor
opens only the member holding the stop places and reads the opening portion of each
line file, so the run stays fast.

**Calendars for Switzerland and the Netherlands** are not implemented. Those feeds use
a different NeTEx calendar shape from the one Luxembourg and France use, and it has not
been validated yet.

## Limits

The figures are a live measurement of five countries, not a general statement about
GTFS and NeTEx. Numbers will differ from the paper, because the paper measured a
snapshot and these feeds keep changing. That difference is the point of running it
continuously.
