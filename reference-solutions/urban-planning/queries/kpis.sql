WITH
feed AS (
    SELECT MIN("start_date") AS f_start, MAX("end_date") AS f_end FROM "MUNICH_DATASET".MVV_CALENDAR
),
base AS (
    SELECT LEAST(GREATEST(CURRENT_DATE, f_start), ADD_DAYS(f_end, -6)) AS b FROM feed
),
rd AS (
    -- first Wednesday on/after today, clamped into the GTFS feed window
    SELECT ADD_DAYS(b, MOD(7 - MOD(DAYS_BETWEEN(b, DATE '1970-01-07'), 7), 7)) AS ref_date FROM base
),
svc AS (
    SELECT c."service_id" FROM "MUNICH_DATASET".MVV_CALENDAR c CROSS JOIN rd
    WHERE c."wednesday" = 1 AND rd.ref_date BETWEEN c."start_date" AND c."end_date"
      AND c."service_id" NOT IN (SELECT x."service_id" FROM "MUNICH_DATASET".MVV_CALENDAR_DATES x CROSS JOIN rd r2
                                 WHERE x."date" = r2.ref_date AND x."exception_type" = 2)
    UNION
    SELECT x."service_id" FROM "MUNICH_DATASET".MVV_CALENDAR_DATES x CROSS JOIN rd
    WHERE x."date" = rd.ref_date AND x."exception_type" = 1
),
lines AS (
    -- S-Bahn lines are stored with route_mode 'Tram'; classify by line name
    SELECT r."route_id", r."route_short_name" AS line,
           CASE WHEN r."route_short_name" REGEXP_LIKE 'S[0-9]+' THEN 'S-Bahn'
                WHEN r."route_short_name" REGEXP_LIKE 'N[0-9]+.*' THEN 'Night'
                WHEN r."route_mode" = 'Rail' THEN 'Regional rail'
                ELSE r."route_mode" END AS line_mode
    FROM "MUNICH_DATASET".MVV_ROUTES r
),
wt AS (
    SELECT t."trip_id", t."direction_id", l.line, l.line_mode
    FROM "MUNICH_DATASET".MVV_TRIPS t
    JOIN svc ON svc."service_id" = t."service_id"
    JOIN lines l ON l."route_id" = t."route_id"
),
ev AS (
    SELECT st."stop_id", wt.line, wt.line_mode
    FROM "MUNICH_DATASET".MVV_STOP_TIMES st JOIN wt ON wt."trip_id" = st."trip_id"
),
stop_dep AS (
    SELECT "stop_id", COUNT(*) AS departures, COUNT(DISTINCT line) AS n_lines
    FROM ev GROUP BY "stop_id"
),
stp AS (
    SELECT s."stop_id", s."stop_name", s."stop_lat", s."stop_lon", s."district_no", d.departures, d.n_lines
    FROM "MUNICH_DATASET".MVV_STOPS s JOIN stop_dep d ON d."stop_id" = s."stop_id"
    WHERE s."in_munich" = 1
),
dist_transit AS (
    SELECT s."district_no",
           COUNT(DISTINCT CASE WHEN s."location_type" = 1 THEN s."stop_id" END) AS stations,
           COUNT(DISTINCT CASE WHEN s."location_type" = 0 THEN s."stop_id" END) AS platforms,
           COALESCE(SUM(d.departures), 0) AS departures
    FROM "MUNICH_DATASET".MVV_STOPS s LEFT JOIN stop_dep d ON d."stop_id" = s."stop_id"
    WHERE s."in_munich" = 1
    GROUP BY s."district_no"
),
dist_lines AS (
    SELECT s."district_no", COUNT(DISTINCT e.line) AS n_lines
    FROM "MUNICH_DATASET".MVV_STOPS s JOIN (SELECT DISTINCT "stop_id", line FROM ev) e ON e."stop_id" = s."stop_id"
    WHERE s."in_munich" = 1 GROUP BY s."district_no"
),
dist_cycle AS (
    SELECT "district_no", SUM("length_m") AS cycle_m
    FROM "MUNICH_DATASET".CYCLING_INFRASTRUCTURE WHERE "path_type" <> 'Dummy' GROUP BY "district_no"
),
supply AS (
    SELECT d."district_no", d."district_name", d."population", d."density_per_ha", d."area_sqm",
           COALESCE(t.stations, 0) AS stations, COALESCE(t.platforms, 0) AS platforms,
           COALESCE(t.departures, 0) AS departures, COALESCE(l.n_lines, 0) AS n_lines,
           COALESCE(c.cycle_m, 0) AS cycle_m,
           ROUND(COALESCE(t.departures, 0) * 1000.0 / d."population", 1) AS dep_per_1k,
           ROUND(d."population" / NULLIF(COALESCE(t.stations, 0), 0)) AS residents_per_station,
           ROUND(COALESCE(c.cycle_m, 0) * 1000.0 / d."population") AS cycle_m_per_1k,
           ROUND(COALESCE(c.cycle_m, 0) / (d."area_sqm" / 1000000.0)) AS cycle_m_per_km2
    FROM "MUNICH_DATASET".DISTRICTS d
    LEFT JOIN dist_transit t ON t."district_no" = d."district_no"
    LEFT JOIN dist_lines l ON l."district_no" = d."district_no"
    LEFT JOIN dist_cycle c ON c."district_no" = d."district_no"
),
idx AS (
    SELECT s.*,
           ROUND(100.0 * (s."density_per_ha" - MIN(s."density_per_ha") OVER ()) / NULLIF(MAX(s."density_per_ha") OVER () - MIN(s."density_per_ha") OVER (), 0)) AS density_idx,
           ROUND(100.0 * (s.dep_per_1k - MIN(s.dep_per_1k) OVER ()) / NULLIF(MAX(s.dep_per_1k) OVER () - MIN(s.dep_per_1k) OVER (), 0)) AS transit_idx,
           ROUND(100.0 * (s.cycle_m_per_1k - MIN(s.cycle_m_per_1k) OVER ()) / NULLIF(MAX(s.cycle_m_per_1k) OVER () - MIN(s.cycle_m_per_1k) OVER (), 0)) AS cycle_idx,
           RANK() OVER (ORDER BY s."density_per_ha" DESC) AS density_rank,
           RANK() OVER (ORDER BY s.dep_per_1k DESC) AS transit_rank,
           RANK() OVER (ORDER BY s.cycle_m_per_1k DESC) AS cycle_rank,
           NTILE(3) OVER (ORDER BY s."density_per_ha" DESC) AS density_tercile,
           NTILE(3) OVER (ORDER BY s.dep_per_1k DESC) AS transit_tercile,
           NTILE(3) OVER (ORDER BY s.cycle_m_per_1k DESC) AS cycle_tercile
    FROM supply s
),
gap AS (
    SELECT i.*,
           (LEAST(i.transit_rank, i.cycle_rank) + GREATEST(i.transit_rank, i.cycle_rank)) / 2.0 - i.density_rank AS gap_raw,
           LEAST(i.transit_rank, i.cycle_rank) - i.density_rank AS best_supply_gap,
           GREATEST(i.transit_rank, i.cycle_rank) - i.density_rank AS worst_supply_gap,
           CASE WHEN i.density_tercile = 1 AND (i.transit_tercile = 3 OR i.cycle_tercile = 3) THEN 1 ELSE 0 END AS flagged,
           CASE WHEN i.density_tercile = 1 AND i.transit_tercile = 3 AND i.cycle_tercile = 3 THEN 'transit + cycling'
                WHEN i.density_tercile = 1 AND i.transit_tercile = 3 THEN 'transit'
                WHEN i.density_tercile = 1 AND i.cycle_tercile = 3 THEN 'cycling'
                ELSE NULL END AS flag_reason
    FROM idx i
)
SELECT
    ROUND(SUM("population") / NULLIF(SUM(stations), 0)) AS residents_per_station,
    ROUND(SUM(departures) * 1000.0 / SUM("population"), 1) AS dep_per_1k,
    ROUND(SUM(cycle_m) * 1000.0 / SUM("population")) AS cycle_m_per_1k,
    SUM(flagged) AS districts_flagged,
    SUM(CASE WHEN flagged = 1 THEN "population" ELSE 0 END) AS residents_in_flagged,
    (SELECT COUNT(*) FROM "MUNICH_DATASET".MVV_STOPS WHERE "in_munich" = 0) AS stops_outside_munich,
    (SELECT TO_CHAR(ref_date, 'YYYY-MM-DD') FROM rd) AS ref_weekday
FROM gap
