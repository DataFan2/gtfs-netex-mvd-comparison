# Data sources

Raw datasets are not included in this repository (see `.gitignore`). Download the files listed
below for each country and place them in that country's `data/raw/` folder before running its
notebook. Each notebook regenerates its own `data/processed/` outputs (also gitignored) when run
top to bottom.

---

## DACH

### Austria

**GTFS**
- Provider: ÖBB (Österreichische Bundesbahnen), Austrian national railway operator
- Dataset page: https://data.oebb.at/de/datensaetze~soll-fahrplan-gtfs~
- File used: `GTFS_Fahrplan_2026.zip`
- Coverage: ÖBB Fahrplan (timetable), validity 2025-12-14 to 2026-12-12
- Access: no registration required — direct download

**NeTEx**
- Provider: Mobilitätsverbünde Austria (regional transport associations open data portal)
- Dataset page: https://data.mobilitaetsverbuende.at
- File used: `netex_evu_2026.zip`
- Coverage: same validity window as GTFS (2025-12-14 to 2026-12-12)
- Access: **registration required** — create an account on the portal before downloading (no direct/deep link is available without an account, so only the portal homepage is listed above)

Notebook: `DACH/MVD Austria/Austria.ipynb`

---

### Switzerland

**GTFS**
- Provider: Open Data Platform Mobility Switzerland (opentransportdata.swiss), operated by the Swiss Federal Office of Transport (BAV)
- Dataset page: https://data.opentransportdata.swiss/dataset/timetable-2026-gtfs2020/resource/1d8312b8-7e27-4cc6-b6ac-3207fa92b5b4
- File used: `switzerland_gtfs_2026-04-01.zip`
- Coverage: Timetable 2026, validity 2025-12-14 to 2026-12-12
- Access: no registration required — direct download
- Accessed: 8 April 2026, under license "Non-commercial Allowed / Commercial Allowed / Reference Required"

**NeTEx**
- Provider: Open Data Platform Mobility Switzerland (opentransportdata.swiss), operated by the Swiss Federal Office of Transport (BAV)
- Dataset page: https://data.opentransportdata.swiss/dataset/timetablenetex_2026/resource/cce2bb3c-2221-4f39-ab12-891e6b8dbf1e
- File used: `switzerland_netex_2026-03-31.zip`
- Coverage: same validity window as GTFS (2025-12-14 to 2026-12-12)
- Access: no registration required — direct download
- Accessed: 8 April 2026, under license "Non-commercial Allowed / Commercial Allowed / Reference Required"

Notebook: `DACH/Switzerland/Switzerland_MVD.ipynb`

---

### Germany

**GTFS**
- Provider: DELFI e.V. (Durchgängige Elektronische Fahrgastinformation), the national public transport data aggregator for Germany, distributed via the Deutschlandweite OpenData-Plattform im ÖPNV (DODP ÖPNV), coordinated by Verkehrsverbund Rhein-Ruhr (VRR)
- Dataset page: https://www.opendata-oepnv.de/ht/de/organisation/delfi/startseite?tx_vrrkit_view%5Baction%5D=details&tx_vrrkit_view%5Bcontroller%5D=View&tx_vrrkit_view%5Bdataset_formats%5D%5B0%5D=ZIP&tx_vrrkit_view%5Bdataset_name%5D=deutschlandweite-sollfahrplandaten-gtfs&cHash=01414d5793fcd0abb0f3a2e35176752c
- File used: `20260413_Deutschlandweite Sollfahrplandaten (GTFS).zip`
- Coverage: Deutschlandweite Sollfahrplandaten, validity 2026-03-28 to 2026-12-12
- Access: **registration required** on the platform

**NeTEx**
- Provider: DELFI e.V., same platform as above
- Dataset page: https://www.opendata-oepnv.de/ht/de/organisation/delfi/startseite?tx_vrrkit_view%5Bdataset_name%5D=deutschlandweite-sollfahrplandaten&tx_vrrkit_view%5Bdataset_formats%5D%5B0%5D=ZIP&tx_vrrkit_view%5Baction%5D=details&tx_vrrkit_view%5Bcontroller%5D=View
- File used: `20260413_ Deutschlandweite Sollfahrplandaten (NeTEX).zip`
- Coverage: same validity window as GTFS
- Access: **registration required** on the platform

Both datasets accessed 13 April 2026. Data producer: DELFI e.V. in cooperation with all German federal state transport systems and long-distance rail operators.

Notebook: `DACH/Germany/Germany_MVD.ipynb`

---

## Southern Europe

### Spain

**GTFS — RENFE Media, Larga Distancia y AVE**
- Provider: RENFE Operadora
- Source: Spanish National Access Point (NAP), operated by the Ministry of Transport (`nap.transportes.gob.es`)
- Dataset page: https://nap.transportes.gob.es/Files/Detail/897
- File used: `20260517_000004_RENFE_AVLD.zip`
- Coverage: Renfe medium-distance, long-distance and high-speed (AVE) rail services across Spain
- Updated: 17/05/2026
- Access: **registration required** — a free account must be created on the NAP portal before downloading. Name, email, organisation and job title are required. Access is granted immediately after registration.

**NeTEx — not available**

No NeTEx dataset could be found for Spain through any official source. The Spanish NAP does not
offer NeTEx as a download format — only GTFS-ZIP, GTFS-RT and SIRI are available. Neither Renfe
nor any other Spanish operator publishes NeTEx data publicly. This is despite the EU regulation
(Delegated Regulation 2017/1926) requiring member states to publish multimodal travel information
data in NeTEx format through their National Access Points; Spain's non-compliance with this
requirement is itself a finding of the thesis. Because no NeTEx dataset is available, the
GTFS–NeTEx MVD comparison cannot be performed for Spain — the GTFS dataset is explored on its own
to document data structure and quality.

Notebook: `Italy and Spain/Spain_MVD.ipynb`

---

### Italy

**GTFS — Trenitalia Tuscany**
- Provider: Trenitalia
- Source: Tuscany Open Data Portal (`dati.toscana.it`)
- Dataset page: https://dati.toscana.it/dataset/rt-oraritb
- File used: `trenitalia.gtfs` (ZIP)
- Coverage: Trenitalia rail services in the Tuscany region — regional feed only, no national GTFS source identified for Italy
- License: CC-BY 4.0
- Access: no registration required — direct download

**NeTEx — Trenitalia national (Italian NeTEx profile)**
- Provider: Trenitalia
- Source: Italian National Access Point (NAP), operated by CCISS
- Dataset page: https://www.cciss.it/nap/mmtis/public/catalog/Dataset/1077621
- File used: `IT-IT-TRENITALIA_L1.xml.gz` (dataset listed on the NAP as "IT-IT-TRENITALIA - Profilo NeTEx (Italia) livello 1")
- Format: `gz:xml` (gzip-compressed XML)
- Coverage: Trenitalia national rail network
- License: not explicitly stated on the NAP page
- Access: no registration required — direct download

**Note on dataset scope:** the two feeds do not cover the same geographic scope. GTFS covers
Trenitalia services in Tuscany only, while NeTEx covers the full national Trenitalia network, so
the comparison is not perfectly symmetric and lower match rates on the NeTEx side are expected by
design (see notebook for details).

Notebook: `Italy and Spain/Italy_MVD.ipynb`

---

## Northern Europe

### Finland

**GTFS and NeTEx — Koontipalvelu (Fintraffic national mobility database)**
- Provider: Fintraffic (Finnish National Access Point)
- Source: Koontipalvelu, aggregating public transport data from all Finnish operators (`mobility.mobility-database.fintraffic.fi/en`)
- Files used: `finland_gtfs.zip`, `finland_netex.zip` — both downloaded as single static ZIP files from the Koontipalvelu page above
- License: CC BY 4.0
- Access: no registration or API key required

**Note on the NeTEx feed:** most Finnish operators still work natively in GTFS. Fintraffic's
validation and conversion tool VACO automatically converts GTFS data into NeTEx for operators who
do not produce it themselves, so the Finnish NeTEx feed is largely a converted version of the GTFS
data rather than an independently produced dataset. This is confirmed by Finland's EU ITS Progress
Report 2023. As a result, comparison results for Finland may show artificially high match rates —
not because the two formats are independently consistent, but because NeTEx was largely derived
from GTFS in the first place (see notebook for details).

Notebook: `Northern Europe/Finland_MVD.ipynb`

---

### Norway

**GTFS and NeTEx — Entur (Norwegian National Access Point)**
- Provider: Entur AS — owned by the Norwegian Ministry of Transport
- Source: Entur developer portal (`developer.entur.org`)
- Dataset page: https://developer.entur.org/stops-and-timetable-data
- Files used: `rb_norway-aggregated-gtfs.zip`, `rb_norway-aggregated-netex.zip` (Nordic NeTEx Profile) — both national aggregated files
- License: NLOD (Norwegian Licence for Open Government Data)
- Access: no registration required — direct download
- Accessed: May 2026

**Note on the NeTEx feed:** the Norwegian NeTEx dataset is organised operator-by-operator
(one shared-data file per transport authority, plus one file per line), rather than as a
single national file. Both GTFS and NeTEx use the same `NSR:StopPlace` / `NSR:Quay`
identifier scheme, which makes the station-level comparison unusually direct (see
notebook for details).

Notebook: `Northern Europe/Norway_MVD.ipynb`

---

### Sweden

**GTFS and NeTEx — Trafiklab (Swedish National Access Point)**
- Provider: Trafiklab (`trafiklab.se`), operated by Samtrafiken on behalf of Sweden's
  regional public transport authorities
- Source: Trafiklab developer portal (`developer.trafiklab.se`) — a free account and API
  key are required (Bronze-level keys are approved instantly, up to 50 downloads/month)
- Files used: `GTFS Sverige 2.zip` (`https://api.resrobot.se/gtfs/sweden.zip?key={apikey}`),
  `NeTEx Sweden Static data.zip` (`https://opendata.samtrafiken.se/netex-sweden/sweden.zip?key={apikey}`)
- License: CC0 1.0 (Public Domain)
- Access: **registration required** — free account + API key via the Trafiklab developer portal
- Both feeds are updated daily

**Note on dataset scope and matching method:** the NeTEx Sweden feed does not yet cover all
Swedish operators, while GTFS Sverige 2 provides full national coverage, so GTFS-only and
NeTEx-only stops/lines are expected. Unlike Norway, GTFS and NeTEx do not share a common stop
or calendar identifier scheme in Sweden, so the station-level comparison uses coordinate
proximity (nearest NeTEx `StopPlace` within 100m) instead of ID matching, and the calendar
comparison is done entirely at the activity-pattern level rather than by ID overlap (see
notebook for details).

Notebook: `Northern Europe/Sweden_MVD.ipynb`

---

## Western Europe

### Belgium

**GTFS — iRail (community)**
- Provider: iRail, a community-driven open transport data initiative for Belgium
- Source: `https://gtfs.irail.be/nmbs/gtfs/`
- File used: `gtfs-nmbs-2026-05-31.zip`
- Coverage: SNCB/NMBS national rail network
- License: iRail open data — based on SNCB/NMBS official timetable data
- Access: no registration required — direct download
- Accessed: 31 May 2026
- Note: this is a community republication of SNCB/NMBS's official timetable data, not a direct official SNCB publication

**NeTEx — not obtained**

SNCB provides NeTEx in the Belgian EPIP profile via `belgiantrain.be`, but access requires
completing a registration form and signing a licence agreement. A request was submitted and
a signed form provided, but no response was received. While the data formally exists, the
lack of open access represents a practical barrier to its use. Because no NeTEx dataset is
available, the GTFS–NeTEx MVD comparison cannot be performed for Belgium — the GTFS dataset
is explored on its own to document data structure and quality (see notebook for details).

Notebook: `Western Europe/Belgium_MVD.ipynb`

---

### France

**GTFS and NeTEx — SNCF Open Data**
- Provider: SNCF (Société Nationale des Chemins de fer Français), French national railway operator
- Source: SNCF Open Data platform (`ressources.data.sncf.com`)
- Files used: `Export_OpenData_SNCF_GTFS_NewTripId.zip`, `export-opendata-sncf-netex.zip`
- Coverage: national SNCF network, validity 2026-04-26 to 2026-09-23 (NeTEx) / 2026-04-26 to 2026-10-31 (GTFS, longer tail)
- Access: no registration required — direct download
- Accessed: 26 April 2026

**Note on the NeTEx feed:** the NeTEx export is a single ~520 MB XML file rather than a
set of smaller resource files, too large to load into memory directly. The notebook extracts
it to disk once, then uses `grep`/`sed` to pull out only the relevant blocks (`StopPlace`,
`Line`, `UicOperatingPeriod`) into much smaller files before parsing them with
`xml.etree.ElementTree`. Unlike the other countries covered so far, France's GTFS `route_id`
and NeTEx `line_id` are literally identical strings, so the line-level comparison uses a
direct ID join rather than coordinate or public-code matching (see notebook for details).

Notebook: `Western Europe/France_MVD.ipynb`

---

### Netherlands

**GTFS — OVapi**
- Provider: OVapi, an open data initiative aggregating all Dutch public transport operators
- Publisher: DOVA (Dienst OV-aanbesteding)
- Source: `https://gtfs.ovapi.nl/nl/`
- File used: `NL-20260505.gtfs.zip` (saved under this name; the dataset page serves the current
  file as `gtfs-nl.zip`)
- Access: no registration required — direct download
- Accessed: May 2026
- License: CC0 (Public Domain)

**NeTEx — NDOV Loket**
- Provider: NDOV Loket (Nationaal Databank Openbaar Vervoer)
- Publisher: DOVA (Dienst OV-aanbesteding)
- Format: NeTEx (European EPIP profile)
- Source: `https://data.ndovloket.nl/netex/epiap/`
- File used: `NeTEx_DOVA_epiap_2026-05-05.xml.gz`
- Access: no registration required — direct download
- Accessed: May 2026
- License: CC0 (Public Domain)

**Note on scope:** the Dutch NeTEx file only publishes `StopPlace` data — no line or calendar
structures are present, so only a station-level comparison is possible for the Netherlands
(unlike the other Western Europe countries). Station matching uses coordinates rather than a
shared ID scheme, since GTFS and NeTEx use unrelated identifiers here.

Notebook: `Western Europe/Netherlands.ipynb`

---

### Luxembourg

**Luxembourg GTFS and NeTEx**
- Provider: Luxembourg Open Data Portal (data.public.lu)
- Publisher: Verkéiersverbond — Luxembourg public transport authority
- GTFS URL: https://data.public.lu/en/datasets/horaires-et-arrets-des-transport-publics-gtfs/
- NeTEx URL: https://data.public.lu/en/datasets/horaires-et-arrets-des-transport-publics-netex/
- Files used: `gtfs-20260408-20260430.zip`, `netex-20260408-20260430.zip`
- License: Creative Commons Attribution 4.0
- Access: no registration required — direct download
- Accessed: April 2026

Notebook: `Western Europe/Luxembourg_MVD.ipynb`

---

## Central and Eastern Europe

### Romania

**GTFS — CFR Călători Romania (community conversion)**
- Provider: CFR Călători (Romanian national passenger railway operator)
- Source: GitHub repository by Vasile Coțovanu, converting the official CFR Călători XML
  timetables published on `data.gov.ro` into GTFS via a community-maintained Ruby script
- Dataset page: https://github.com/vasile/data.gov.ro-gtfs-exporter/tree/master/gtfs-out
- File used: `data.gov.ro-gtfs-exporter-master.zip`
- License: MIT License
- Access: no registration required — direct download

**NeTEx — not available**

No NeTEx dataset could be found for Romania through any official source. Romania does not
publish NeTEx data publicly, so the GTFS–NeTEx MVD comparison cannot be performed — the GTFS
dataset is explored on its own to document data structure and quality (see notebook for
details).

**Note on dataset scope:** the GTFS feed itself is unofficial (a community conversion rather
than a direct CFR Călători publication), but produced a clean, usable dataset covering 1,695
stops and 1,023 routes, including some cross-border stations in Bulgaria and Hungary.

Notebook: `CEE/Romania_MVD.ipynb`

---

### Czech Republic

**GTFS — Spojenka Czech Timetable Dataset**
- Source: Spojenka, an aggregated Czech timetable dataset (`spojenka.cz/jrdata`)
- File used: `jizdnirady-gtfs.zip`
- Coverage: countrywide in scope, mainly trains and integrated transport systems; Spojenka
  notes this is not necessarily a complete official national feed, and recommends JrUtil for
  a more complete database including long-distance lines and private operators
- Underlying sources aggregated by Spojenka: CIS JŘ, PID open data, SŽ timetables, DÚK open
  data, PMDP open data, IDS JMK data, IDZK data, and other regional/operator sources
- License: free for non-commercial use, without warranty
- Access: no registration required — direct download
- Accessed: 18 May 2026 (file updates daily, usually between 04:30 and 04:40)

**NeTEx — Czech National Timetable Data (CIS JŘ)**
- Provider: CIS JŘ, the Czech national timetable information system, published by the Czech
  Ministry of Transport
- Dataset page: https://portal.cisjr.cz/pub/netex/
- File used: `NeTEx_GVD2026_updates_2026-05.zip`
- Coverage: national and regional rail timetable data (GVD 2026 updates)
- License: publicly accessible for non-commercial and commercial use
- Access: no registration required — direct download

**Note on data quality:** Czech transport data expert David Koňařík (FOSDEM 2026) states
that Czech NeTEx data passes XSD validation but is semantically broken and does not fully
follow the specification. The notebook investigates this claim directly (broken references,
ID reuse across files, duplicate stop names and line codes) rather than taking it at face
value — see the "NeTEx Data Quality Investigation" section for the concrete findings. As a
result, the station and route-level GTFS–NeTEx comparisons for the Czech Republic are limited
by identifier scoping issues on the NeTEx side, and the calendar comparison is not attempted
since no reliable link between GTFS services and NeTEx operating periods could be established.

Notebook: `CEE/Czech Republic_MVD.ipynb`
