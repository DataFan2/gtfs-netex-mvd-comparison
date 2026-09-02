# Minimum Viable Denominator: comparing GTFS and NeTEx across Europe

A country-by-country comparison of published GTFS and NeTEx public transport feeds from
15 European countries, using a **Minimum Viable Denominator (MVD)**: the smallest set of
concepts both standards represent and that together suffice to test whether two independently
published feeds can actually be related to one another.

**The question.** GTFS and NeTEx describe the same concepts, are explicitly mapped to each
other, and both derive from Transmodel (EN 12896). Member States publish both under the same
legal mandate. Does that make the published data comparable in practice?

**The finding.** Not reliably. Comparability ranges from complete, symmetric agreement
(Switzerland, France) to total failure (Italy and the Czech Republic on routes, 0%). The
obstacles are operational rather than representational: scattered provenance, reused or
non-unique identifiers, semantically repurposed fields, and differences in scope and
granularity. Shared standards are necessary but not sufficient for interoperable data.

---

## The MVD

Three dimensions, chosen because they are the minimum data categories required by *Level of
Service 1* of EU Delegated Regulation 2017/1926, and because they answer the three questions
any journey planner must resolve first:

| Dimension | Question | GTFS | NeTEx |
|---|---|---|---|
| Stops / stations | Where can a passenger board? | `stops.txt` | `StopPlace` |
| Routes / lines | Where does the service go? | `routes.txt` | `Line` |
| Service calendars | When does it run? | `calendar.txt`, `calendar_dates.txt` | `DayType`, `DayTypeAssignment`, `OperatingPeriod`, `UicOperatingPeriod` |

Each dimension is reported as **two coverage rates**, one per side, rather than a single
symmetric score. The asymmetries are informative: a high GTFS rate against a low NeTEx rate
means GTFS is a subset of a richer NeTEx, not that the two disagree.

## Coverage

A usable GTFS feed was found for all 15 countries surveyed. NeTEx was the constraint:

| | Countries | Notes |
|---|---|---|
| Surveyed | 15 | AT, BE, CH, CZ, DE, ES, FI, FR, IT, LU, NL, NO, PL, RO, SE |
| Stop comparison | 10 | |
| Route comparison | 9 | NL excluded; its NeTEx feed contains no lines |
| Calendar comparison | 6 | |
| No usable NeTEx | 4 | BE, ES, PL, RO |
| NeTEx too fragmented | 2 | DE (per-line files, no national dataset), FI (calendars only) |

## Repository contents

| Path | Contents |
|---|---|
| `DACH/` | Austria, Switzerland, Germany |
| `Western Europe/` | France, Luxembourg, Netherlands, Belgium |
| `Northern Europe/` | Finland, Norway, Sweden |
| `Italy and Spain/` | Italy, Spain |
| `CEE/` | Czech Republic, Poland, Romania |
| `Calendar_Unified_Method/` | The single calendar comparison rule applied to all six countries |
| `DATA_SOURCES.md` | Provenance for every feed: source, publisher, file name, licence, access date |
| `SUPPLEMENTARY_MATERIAL.pdf` | Extended methodology, per-country matching procedures, all overlap diagrams |
| `requirements.txt` | Python dependencies |

Each country notebook carries out the stop, route and, where possible, calendar comparison for
that country, and states its own data source at the top.

The calendar comparison is implemented once and applied identically everywhere: active dates
are restricted to a shared comparison window, encoded as day-by-day bit strings, and compared
as sets of unique patterns. The country notebooks supply only the extraction step that precedes
it, which differs because NeTEx calendar information is split across several linked elements
that publishers populate differently.

## Reproducing the analysis

```bash
pip install -r requirements.txt
```

Raw feeds are **not** redistributed here. They belong to their publishers, and several require
registration. To reproduce:

1. Download each feed from the source listed in [`DATA_SOURCES.md`](DATA_SOURCES.md)
2. Place it in that country's `data/raw/` folder
3. Run the country notebook top to bottom; it regenerates its own `data/processed/` outputs

Both `data/raw/` and `data/processed/` are gitignored.

**Feeds change.** This analysis is a single snapshot, with per-feed access dates recorded in
`DATA_SOURCES.md`. Results are not expected to reproduce exactly against later versions of the
same sources.

## Limitations

- The three dimensions do not demonstrate the same thing. A stop match evidences a shared
  location; a route-label match a shared public label; a calendar-pattern match a shared
  active-day sequence rather than the same service.
- Proximity thresholds for coordinate-based stop matching (50 to 100 m) and the 50% / 80%
  interpretive bands are conventions, not derived values.
- Sample sizes differ by orders of magnitude between countries, from 313 Italian stops to
  89,547 Finnish ones, so percentages are not equally precise.
- Some feeds are not like-for-like in scope. Italy's GTFS covers Tuscany only while its NeTEx
  covers the national network; Finland's NeTEx is largely a machine conversion of its own GTFS.
  Both are documented in `DATA_SOURCES.md`.
- The MVD covers stops, routes and calendars only. Fares, accessibility and real-time data are
  out of scope and may behave differently.

## Paper

> Livia Mihaela Miclaus and Shahrom Sohi. *It is Not the Standard, It is the Feed: Analysis of
> a Minimum Viable Denominator for Comparing GTFS and NeTEx in European Public Transport Data.*
> Currently under review at the International Conference on Semantic Systems (SEMANTiCS).

This repository is the companion code and data documentation for that paper, and derives from
a bachelor thesis at the Vienna University of Economics and Business (WU Wien). The
[supplementary material](SUPPLEMENTARY_MATERIAL.pdf) contains the extended methodology and the
full set of per-country overlap diagrams that did not fit within the paper's page limit.

## Licence

Code in this repository is released under the **MIT Licence**. Documentation and the
supplementary material are released under **CC BY 4.0**.

The underlying transport feeds are covered by neither. Each carries its own licence, recorded
per feed in `DATA_SOURCES.md`.

## Authors

**Livia Mihaela Miclaus** and **Shahrom Sohi**, Vienna University of Economics and Business
(WU Wien), Institute for Data, Process and Knowledge Management.
