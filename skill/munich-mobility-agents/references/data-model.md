# MUNICH_DATASET data model

Schema `MUNICH_DATASET`, loaded by `EXAKIT_SCHEMA=MUNICH_DATASET exakit data-load ~/munich-open-data` from the flat folder that `prepare_dataset.py` writes. One table per file, table name = file name upper-cased. Column names below are the CSV headers; confirm their types with `describe_exasol_tables_and_views` because a CSV load may leave dates and decimals as VARCHAR.

All coordinates are **WGS84** (`lat`, `lon` in degrees). Every point table carries `district_no` (1–25) computed by point-in-polygon against the district boundaries, so district joins are plain equality joins. Polygons are WKT in WGS84 with `lon lat` order.

## Tables

### DISTRICTS (25 rows) — Munich's 25 Stadtbezirke
| column | meaning |
|---|---|
| district_no | 1–25, the join key everywhere |
| district_name | e.g. Altstadt-Lehel |
| population, population_pct | residents and share of city |
| area_ha, area_pct, area_sqm | area |
| density_per_ha | residents per hectare |
| centroid_lat, centroid_lon | centroid for maps |
| polygon_wkt | POLYGON/MULTIPOLYGON in WGS84 |

### ROADWORKS (~5,700 rows) — current and planned roadworks, four-week horizon
| column | meaning |
|---|---|
| roadwork_id, source_id | ids |
| street | street and house-number range |
| affected_areas | e.g. Gehweg, Fahrbahn, Radweg, Parken (concatenated) |
| description | free text (German) |
| impact | e.g. Vollsperrung, Halbseitige Sperre, Wegfall einer Fahrspur, Fahrbahn verengt, Gehweg gesperrt |
| kind | type of works |
| start_date, end_date | YYYY-MM-DD (start_raw / end_raw keep the original) |
| centroid_lat, centroid_lon, district_no | location |
| shape_wkt | polygon in WGS84 |

### MVV_STOPS (~28,000 rows; ~4,100 inside Munich) — GTFS stops
| column | meaning |
|---|---|
| stop_id, stop_code, stop_name | id and name |
| stop_lat, stop_lon | WGS84 |
| location_type | 1 = station (parent), 0/empty = platform/stop |
| parent_station | id of the parent station |
| district_no, in_munich | district (empty outside Munich), 1/0 flag |

### MVV_ROUTES (~900), MVV_TRIPS (~113,000), MVV_STOP_TIMES (~4M), MVV_CALENDAR (~1,700), MVV_CALENDAR_DATES (~9,600), MVV_AGENCY (~100) — GTFS
- `MVV_ROUTES`: route_id, agency_id, route_short_name, route_long_name, route_type (GTFS code), **route_mode** (decoded: S-Bahn, U-Bahn, Tram, Bus, Rail, …), route_color.
- `MVV_TRIPS`: route_id, service_id, trip_id, trip_headsign, direction_id.
- `MVV_STOP_TIMES`: trip_id, arrival_time, departure_time (text HH:MM:SS, may exceed 24:00), stop_id, stop_sequence.
- `MVV_CALENDAR`: service_id, monday..sunday (1/0), start_date, end_date (YYYY-MM-DD). `MVV_CALENDAR_DATES`: service_id, date, exception_type (1 added, 2 removed).
- Feed covers 2026-09-01 to 2026-11-30. **Scheduled service only: no passengers, delays, crowding or live positions.**

### BIKE_COUNTS_DAILY (~970 rows) — permanent bicycle counters, one row per counter per day, with weather
| column | meaning |
|---|---|
| count_date | YYYY-MM-DD, Jan–Jul 2026 |
| station | Arnulf, Erhardt, Hirsch, Kreuther, Margareten, Olympia |
| dir_1, dir_2, total | counts per direction and total |
| temp_min_c, temp_max_c | °C |
| rain_mm, cloud_cover_pct, sunshine_hours | weather that day |

### BIKE_COUNTS_15MIN (~93,000 rows) — same counters, 15-minute resolution
count_date, time_start, time_end (HH:MM), station, dir_1, dir_2, total.

### BIKE_COUNT_STATIONS (6 rows)
station, station_name, lat, lon, direction_1, direction_2, district_no. (Arnulf is missing in May–July 2026.)

### CYCLING_INFRASTRUCTURE (~21,000 rows) — cycle-path segments maintained by the city
segment_id, street, length_m, path_type (e.g. Getrennter Rad- und Gehweg, Radfahrstreifen, Fahrradstraße …), start_lat/lon, end_lat/lon, mid_lat/lon, district_no.

### MVG_BIKE_TRIPS (optional, only if prepared with --with-mvg-bikes)
trip_no, start_time, end_time, start_lat/lon, end_lat/lon, rental_is_station, rental_station_name, return_is_station, return_station_name, year. **Historical only: the MVG Rad service ended in September 2025.**

## Joins
- District rollups: `X.district_no = DISTRICTS.district_no` for stops, roadworks, cycle segments, counters.
- Departures per stop: `MVV_STOP_TIMES st JOIN MVV_TRIPS t ON st.trip_id = t.trip_id JOIN MVV_ROUTES r ON t.route_id = r.route_id JOIN MVV_CALENDAR c ON t.service_id = c.service_id` — filter `c.tuesday = 1` (or any weekday) and a date inside the feed window for a typical weekday.
- Proximity: filter both sides to the same `district_no` (or neighbouring ones) first, then apply the distance below. A full cross join of roadworks × stops is 160M pairs; the district filter cuts it to a few million, which Exasol handles in seconds.

## Haversine distance in metres (Exasol SQL)
```sql
2 * 6371000 * ASIN(SQRT(
    POWER(SIN(RADIANS(b.lat - a.lat) / 2), 2) +
    COS(RADIANS(a.lat)) * COS(RADIANS(b.lat)) * POWER(SIN(RADIANS(b.lon - a.lon) / 2), 2)
)) AS distance_m
```
Exasol also has GIS functions (`ST_GEOMFROMTEXT`, `ST_POINT`, `ST_CONTAINS`, `ST_DISTANCE`, `ST_INTERSECTS`) on `GEOMETRY` columns; `polygon_wkt` and `shape_wkt` can be wrapped in `ST_GEOMFROMTEXT(...)` for point-in-polygon or intersection questions. Distances from `ST_DISTANCE` on lat/lon are in degrees, so prefer the haversine above for metres.

## Casting when columns arrived as VARCHAR
```sql
TO_DATE(count_date, 'YYYY-MM-DD')           -- dates
CAST(total AS DECIMAL(18,2))                -- numbers
CAST(rain_mm AS DECIMAL(10,2)) > 1          -- rainy day
```

## Known gaps (say them)
- No passenger counts, delays, crowding, live traffic or event data.
- Six counters for the whole city; Arnulf missing May–July.
- Roadworks horizon is the next four weeks from the download date (September 2026 snapshot).
- GTFS `shapes` is empty in this feed, so route geometry is not available; use stop sequences.
- Population figures are a point-in-time snapshot from the portal.
