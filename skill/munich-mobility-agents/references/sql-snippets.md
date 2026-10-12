# SQL building blocks for MUNICH_DATASET

These are the pieces every persona query needs and that take longest to get right the first time. They are
infrastructure, not answers: the joins, the score, the ranking and the interpretation are yours.

## Representative weekday and the services that run on it

The feed covers 2026-09-01 to 2026-11-30. Pick the first Wednesday on or after today, clamped into the window,
and include the calendar exceptions.

```sql
WITH feed AS (
    SELECT MIN("start_date") AS f_start, MAX("end_date") AS f_end FROM MUNICH_DATASET.MVV_CALENDAR
),
base AS (SELECT LEAST(GREATEST(CURRENT_DATE, f_start), ADD_DAYS(f_end, -6)) AS b FROM feed),
rd AS (SELECT ADD_DAYS(b, MOD(7 - MOD(DAYS_BETWEEN(b, DATE '1970-01-07'), 7), 7)) AS ref_date FROM base),
svc AS (
    SELECT c."service_id" FROM MUNICH_DATASET.MVV_CALENDAR c CROSS JOIN rd
    WHERE c."wednesday" = 1 AND rd.ref_date BETWEEN c."start_date" AND c."end_date"
      AND c."service_id" NOT IN (SELECT x."service_id" FROM MUNICH_DATASET.MVV_CALENDAR_DATES x CROSS JOIN rd r2
                                 WHERE x."date" = r2.ref_date AND x."exception_type" = 2)
    UNION
    SELECT x."service_id" FROM MUNICH_DATASET.MVV_CALENDAR_DATES x CROSS JOIN rd
    WHERE x."date" = rd.ref_date AND x."exception_type" = 1
)
SELECT (SELECT ref_date FROM rd) AS ref_weekday, COUNT(*) AS services FROM svc
```

## Line mode by name (S-Bahn is stored as Tram)

```sql
lines AS (
    SELECT r."route_id", r."route_short_name" AS line,
           CASE WHEN r."route_short_name" REGEXP_LIKE 'S[0-9]+' THEN 'S-Bahn'
                WHEN r."route_short_name" REGEXP_LIKE 'N[0-9]+.*' THEN 'Night'
                WHEN r."route_mode" = 'Rail' THEN 'Regional rail'
                ELSE r."route_mode" END AS line_mode
    FROM MUNICH_DATASET.MVV_ROUTES r
)
```

## Scheduled departures per stop on that weekday

```sql
wt AS (
    SELECT t."trip_id", t."direction_id", l.line, l.line_mode
    FROM MUNICH_DATASET.MVV_TRIPS t JOIN svc ON svc."service_id" = t."service_id"
    JOIN lines l ON l."route_id" = t."route_id"
),
ev AS (SELECT st."stop_id", wt.line, wt.line_mode FROM MUNICH_DATASET.MVV_STOP_TIMES st JOIN wt ON wt."trip_id" = st."trip_id"),
stop_dep AS (SELECT "stop_id", COUNT(*) AS departures, COUNT(DISTINCT line) AS n_lines FROM ev GROUP BY "stop_id")
```
Join `stop_dep` to `MVV_STOPS` and filter `"in_munich" = 1` for anything per district. Trips per line and direction
(`GROUP BY line, "direction_id"` over `wt`) give the frequency; "high-frequency" is a threshold you choose and state.

## Distance in metres with a cheap prefilter

```sql
-- a: roadwork centroids, b: stops (or cycle segment midpoints). Bounding box first, haversine second.
FROM a JOIN b
  ON b."stop_lat" BETWEEN a."centroid_lat" - 0.0015 AND a."centroid_lat" + 0.0015
 AND b."stop_lon" BETWEEN a."centroid_lon" - 0.0023 AND a."centroid_lon" + 0.0023
WHERE 2 * 6371000 * ASIN(SQRT(
        POWER(SIN(RADIANS(b."stop_lat" - a."centroid_lat") / 2), 2)
      + COS(RADIANS(a."centroid_lat")) * COS(RADIANS(b."stop_lat"))
      * POWER(SIN(RADIANS(b."stop_lon" - a."centroid_lon") / 2), 2))) <= 150
```
0.0015° of latitude is about 165 m; 0.0023° of longitude about 170 m at Munich's latitude. Widen both for a larger
radius. Do not restrict to the same district: it drops pairs across a border.

## Open roadworks

```sql
rw AS (
    SELECT * FROM MUNICH_DATASET.ROADWORKS
    WHERE "end_date" >= CURRENT_DATE
      AND ("start_date" IS NULL OR "start_date" <= ADD_DAYS(CURRENT_DATE, {horizon!d}))   -- NULL start = "began over a year ago"
)
```

## Weekday or weekend, dry or rainy

```sql
CASE WHEN TO_CHAR("count_date", 'ID') IN ('6', '7') THEN 'weekend' ELSE 'weekday' END AS day_type,
CASE WHEN "rain_mm" <= 1 THEN 'dry' ELSE 'rainy' END AS wx
```
`TO_CHAR(date, 'ID')` is the ISO weekday (1 = Monday). The 15-minute table has `time_start` as text `HH:MM`;
`TO_NUMBER(SUBSTR("time_start", 1, 2))` is the hour.

## Index 0 to 100 across districts, and ranks

```sql
ROUND(100.0 * (x - MIN(x) OVER ()) / NULLIF(MAX(x) OVER () - MIN(x) OVER (), 0)) AS x_idx,
RANK() OVER (ORDER BY x DESC) AS x_rank,
NTILE(3) OVER (ORDER BY x DESC) AS x_tercile
```

## Things that break

- Unquoted lowercase columns (`district_no` instead of `"district_no"`): "object DISTRICT_NO not found".
- `AS hour`, `AS month`, `AS value`, `AS count`, `AS type`: reserved; use `hour_of_day`, `month_key`, or quote the alias.
- `UNION ALL` between top-level SELECTs through the exasol MCP tool: rejected; wrap in `WITH` or run separately.
- `:name` placeholders: rejected; dashboards use `{name!d}` / `{name!s}` / `{name!f}`.
