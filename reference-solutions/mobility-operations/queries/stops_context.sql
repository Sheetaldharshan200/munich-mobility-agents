WITH
feed AS (
    SELECT MIN("start_date") AS f_start, MAX("end_date") AS f_end FROM "MUNICH_DATASET".MVV_CALENDAR
),
base AS (
    SELECT LEAST(GREATEST(CURRENT_DATE, f_start), ADD_DAYS(f_end, -6)) AS b FROM feed
),
rd AS (
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
freq AS (
    SELECT line_mode, line, MAX(n) AS trips_per_dir
    FROM (SELECT line_mode, line, "direction_id", COUNT(*) AS n FROM wt GROUP BY line_mode, line, "direction_id") f
    GROUP BY line_mode, line
),
hf AS (
    SELECT line_mode, line, trips_per_dir FROM freq WHERE trips_per_dir >= 100 AND line_mode <> 'Night'
),
ev AS (
    SELECT st."stop_id", wt.line, wt.line_mode
    FROM "MUNICH_DATASET".MVV_STOP_TIMES st JOIN wt ON wt."trip_id" = st."trip_id"
),
stop_dep AS (
    SELECT "stop_id", COUNT(*) AS departures, COUNT(DISTINCT line) AS n_lines, COUNT(DISTINCT line_mode) AS n_modes
    FROM ev GROUP BY "stop_id"
),
stp AS (
    SELECT s."stop_id", s."stop_name", s."stop_lat", s."stop_lon", s."district_no",
           d.departures, d.n_lines, d.n_modes
    FROM "MUNICH_DATASET".MVV_STOPS s JOIN stop_dep d ON d."stop_id" = s."stop_id"
    WHERE s."in_munich" = 1
),
stop_hf AS (
    SELECT DISTINCT ev."stop_id", ev.line_mode, ev.line, hf.trips_per_dir
    FROM ev JOIN hf ON hf.line_mode = ev.line_mode AND hf.line = ev.line
)
SELECT "stop_name" AS stop_name, "stop_lat" AS lat, "stop_lon" AS lon, departures, n_lines
FROM stp
WHERE departures >= 100
ORDER BY departures DESC
