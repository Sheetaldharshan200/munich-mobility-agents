# Data verification: source vs. loaded

Checked on 2026-10-12 against the portal download (`munich-open-data.zip`). Row counts are parsed with a CSV reader (so multi-line descriptions count as one row), then compared with the output files and with `EXA_ALL_TABLES` after `exakit data-load`.

| Table | Source file(s) | Source rows | Output rows | Loaded rows |
|---|---|---:|---:|---:|
| BIKE_COUNTS_DAILY | 7 × rad_2026_MM_tage.csv | 972 | 972 | 972 |
| BIKE_COUNTS_15MIN | 7 × rad_2026_MM_15min.csv | 93,312 | 93,312 | 93,312 |
| BIKE_COUNT_STATIONS | Munich geoportal, 6 counters | 6 | 6 | 6 |
| DISTRICTS | stadtbezirke.csv + bevolkerung_bezirke_neu.csv | 27 polygon rows / 26 population rows | 25 | 25 |
| ROADWORKS | baustellen.csv | 5,702 | 5,702 | 5,702 |
| CYCLING_INFRASTRUCTURE | radwege_t2.csv | 21,172 | 21,172 | 21,172 |
| MVV_AGENCY | agency.csv | 99 | 99 | 99 |
| MVV_ROUTES | routes.csv | 906 | 906 | 906 |
| MVV_TRIPS | trips.csv | 112,882 | 112,882 | 112,882 |
| MVV_STOPS | stops.csv | 28,330 | 28,330 | 28,330 |
| MVV_STOP_TIMES | stop_times.csv (byte copy, LF endings) | 2,176,946 | 2,176,946 | 2,176,946 |
| MVV_CALENDAR | calendar.csv | 1,734 | 1,734 | 1,734 |
| MVV_CALENDAR_DATES | calendar_dates.csv | 9,638 | 9,638 | 9,638 |
| MVV_FEED_INFO | feed_info.csv | 1 | 1 | 1 |
| MVV_TICKETING_DEEP_LINKS | ticketing_deep_links.csv | 1 | 1 | 1 |

**DISTRICTS, 27 → 25:** districts 18 and 19 are stored as two polygon parts each in the boundary file; they are merged into one MULTIPOLYGON row per district, nothing is dropped. The population file's 26th row is the city total ("insgesamt"), not a district, and is not loaded.

**Columns:** every source column is kept, renamed to English snake_case. Added columns: WGS84 `lat`/`lon` (converted from UTM 32N), `centroid_*`, `mid_*`, `district_no`, `in_munich`, `route_mode`, `start_raw`/`end_raw` (the original date text). Values are unchanged except: dates normalised to `YYYY-MM-DD`, decimal commas to points, thousands-separator spaces removed from population, and a non-date roadwork start ("Beginn vor mehr als einem Jahr", 45 rows) stored as NULL in `start_date` with the text kept in `start_raw`.

**Not loaded, and why**

| File | Reason |
|---|---|
| stadtbezirke_geo.json, baustellen_geo.json | Same geometry as the `shape` column of the CSVs, already loaded as `polygon_wkt` / `shape_wkt` |
| shapes.csv | Header only, no rows in this feed; exapump cannot load an empty file |
| ticketing_identifiers.csv | Ticket-shop identifiers per stop, no analytical use; included automatically by `prepare_dataset.py` when the file is present in the archive |
| MVG_Rad_Fahrten_2015–2025.csv | Optional historical dataset, ~1.5 GB; `prepare_dataset.py --with-mvg-bikes 2024 2025` adds it |
