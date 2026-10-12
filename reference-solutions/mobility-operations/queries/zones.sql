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
),
rw AS (
    SELECT r."roadwork_id", r."street", r."district_no", r."kind", r."impact", r."affected_areas",
           SUBSTR(r."description", 1, 200) AS description,
           r."start_date", r."start_raw", r."end_date", r."centroid_lat", r."centroid_lon",
           CASE WHEN r."start_date" > CURRENT_DATE THEN 'Planned' ELSE 'Active' END AS status,
           CASE WHEN LOWER(COALESCE(r."impact", '')) LIKE '%sperrung%'
                  OR LOWER(COALESCE(r."impact", '')) LIKE '%sperre%'
                  OR LOWER(COALESCE(r."impact", '')) LIKE '%vollsperr%'
                  OR LOWER(COALESCE(r."impact", '')) LIKE '%halbseitig%'
                  OR LOWER(COALESCE(r."impact", '')) LIKE '%fahrspur%' THEN 1 ELSE 0 END AS closure,
           CASE WHEN LOWER(COALESCE(r."affected_areas", '')) LIKE '%fahrbahn%' THEN 1 ELSE 0 END AS carriageway,
           DAYS_BETWEEN(LEAST(r."end_date", ADD_DAYS(CURRENT_DATE, 27)),
                        GREATEST(COALESCE(r."start_date", CURRENT_DATE), CURRENT_DATE)) + 1 AS days_in_window
    FROM "MUNICH_DATASET".ROADWORKS r
    WHERE r."end_date" >= CURRENT_DATE
      AND (r."start_date" IS NULL OR r."start_date" <= ADD_DAYS(CURRENT_DATE, {horizon!d}))
      AND r."centroid_lat" IS NOT NULL
      AND ({kind!s} = 'all' OR r."kind" = {kind!s})
),
near_stop AS (
    SELECT rw."roadwork_id", stp."stop_id", stp."stop_name", stp.departures, stp.n_lines,
           2 * 6371000 * ASIN(SQRT(POWER(SIN(RADIANS(stp."stop_lat" - rw."centroid_lat") / 2), 2) + COS(RADIANS(rw."centroid_lat")) * COS(RADIANS(stp."stop_lat")) * POWER(SIN(RADIANS(stp."stop_lon" - rw."centroid_lon") / 2), 2))) AS dist_m
    FROM rw JOIN stp
      ON stp."stop_lat" BETWEEN rw."centroid_lat" - 0.0015 AND rw."centroid_lat" + 0.0015
     AND stp."stop_lon" BETWEEN rw."centroid_lon" - 0.0023 AND rw."centroid_lon" + 0.0023
    WHERE 2 * 6371000 * ASIN(SQRT(POWER(SIN(RADIANS(stp."stop_lat" - rw."centroid_lat") / 2), 2) + COS(RADIANS(rw."centroid_lat")) * COS(RADIANS(stp."stop_lat")) * POWER(SIN(RADIANS(stp."stop_lon" - rw."centroid_lon") / 2), 2))) <= 150
),
seg AS (
    SELECT "segment_id", "street", "length_m", "mid_lat", "mid_lon" FROM "MUNICH_DATASET".CYCLING_INFRASTRUCTURE WHERE "path_type" <> 'Dummy'
),
near_seg AS (
    SELECT rw."roadwork_id", seg."segment_id", seg."street" AS seg_street, seg."length_m"
    FROM rw JOIN seg
      ON seg."mid_lat" BETWEEN rw."centroid_lat" - 0.001 AND rw."centroid_lat" + 0.001
     AND seg."mid_lon" BETWEEN rw."centroid_lon" - 0.0015 AND rw."centroid_lon" + 0.0015
    WHERE 2 * 6371000 * ASIN(SQRT(POWER(SIN(RADIANS(seg."mid_lat" - rw."centroid_lat") / 2), 2) + COS(RADIANS(rw."centroid_lat")) * COS(RADIANS(seg."mid_lat")) * POWER(SIN(RADIANS(seg."mid_lon" - rw."centroid_lon") / 2), 2))) <= 100
),
ctr AS (
    SELECT b."station", b."station_name", b."lat", b."lon", AVG(d."total") AS avg_daily
    FROM "MUNICH_DATASET".BIKE_COUNT_STATIONS b JOIN "MUNICH_DATASET".BIKE_COUNTS_DAILY d ON d."station" = b."station"
    GROUP BY b."station", b."station_name", b."lat", b."lon"
),
near_ctr AS (
    SELECT rw."roadwork_id", ctr."station_name", ctr.avg_daily,
           ROW_NUMBER() OVER (PARTITION BY rw."roadwork_id" ORDER BY ctr.avg_daily DESC) AS rn
    FROM rw CROSS JOIN ctr
    WHERE 2 * 6371000 * ASIN(SQRT(POWER(SIN(RADIANS(ctr."lat" - rw."centroid_lat") / 2), 2) + COS(RADIANS(rw."centroid_lat")) * COS(RADIANS(ctr."lat")) * POWER(SIN(RADIANS(ctr."lon" - rw."centroid_lon") / 2), 2))) <= 300
),
agg_stop AS (
    SELECT "roadwork_id", COUNT(*) AS stops_150m, SUM(departures) AS departures_150m, MIN(dist_m) AS nearest_stop_m
    FROM near_stop GROUP BY "roadwork_id"
),
nearest AS (
    SELECT "roadwork_id", "stop_name" AS nearest_stop
    FROM (SELECT ns."roadwork_id", ns."stop_name", ROW_NUMBER() OVER (PARTITION BY "roadwork_id" ORDER BY dist_m) AS rn FROM near_stop ns) x
    WHERE rn = 1
),
rw_lines AS (
    SELECT "roadwork_id", COUNT(*) AS lines_150m,
           SUM(CASE WHEN is_hf = 1 THEN 1 ELSE 0 END) AS hf_lines_150m,
           LISTAGG(CASE WHEN is_hf = 1 THEN line END, ', ') WITHIN GROUP (ORDER BY line) AS hf_lines
    FROM (SELECT DISTINCT ns."roadwork_id", ev.line_mode, ev.line,
                 CASE WHEN hf.line IS NOT NULL THEN 1 ELSE 0 END AS is_hf
          FROM near_stop ns
          JOIN (SELECT DISTINCT "stop_id", line_mode, line FROM ev) ev ON ev."stop_id" = ns."stop_id"
          LEFT JOIN hf ON hf.line_mode = ev.line_mode AND hf.line = ev.line) l
    GROUP BY "roadwork_id"
),
agg_seg AS (
    SELECT "roadwork_id", SUM("length_m") AS cycle_m_100m, COUNT(*) AS cycle_segments
    FROM near_seg GROUP BY "roadwork_id"
),
seg_street AS (
    SELECT "roadwork_id", seg_street AS cycle_street
    FROM (SELECT "roadwork_id", seg_street, ROW_NUMBER() OVER (PARTITION BY "roadwork_id" ORDER BY SUM("length_m") DESC) AS rn
          FROM near_seg WHERE seg_street IS NOT NULL GROUP BY "roadwork_id", seg_street) x
    WHERE rn = 1
),
scored AS (
    SELECT rw."roadwork_id", rw."street", rw."district_no", rw."kind", rw."impact", rw."affected_areas", rw.description,
           rw."start_date", rw."start_raw", rw."end_date", rw."centroid_lat", rw."centroid_lon", rw.status,
           rw.closure, rw.carriageway, rw.days_in_window, dd."district_name",
           COALESCE(a.stops_150m, 0) AS stops_150m,
           COALESCE(a.departures_150m, 0) AS departures_150m,
           ROUND(a.nearest_stop_m) AS nearest_stop_m, n.nearest_stop,
           COALESCE(l.lines_150m, 0) AS lines_150m,
           COALESCE(l.hf_lines_150m, 0) AS hf_lines_150m, l.hf_lines,
           ROUND(COALESCE(s.cycle_m_100m, 0)) AS cycle_m_100m, ss.cycle_street,
           c."station_name" AS bike_counter, ROUND(c.avg_daily) AS counter_avg_daily,
           ROUND((LN(1 + COALESCE(a.departures_150m, 0))
                  + COALESCE(s.cycle_m_100m, 0) / 100
                  + 2 * rw.closure + rw.carriageway)
                 * LEAST(rw.days_in_window, 28) / 28, 2) AS score
    FROM rw
    LEFT JOIN "MUNICH_DATASET".DISTRICTS dd ON dd."district_no" = rw."district_no"
    LEFT JOIN agg_stop a ON a."roadwork_id" = rw."roadwork_id"
    LEFT JOIN nearest n ON n."roadwork_id" = rw."roadwork_id"
    LEFT JOIN rw_lines l ON l."roadwork_id" = rw."roadwork_id"
    LEFT JOIN agg_seg s ON s."roadwork_id" = rw."roadwork_id"
    LEFT JOIN seg_street ss ON ss."roadwork_id" = rw."roadwork_id"
    LEFT JOIN near_ctr c ON c."roadwork_id" = rw."roadwork_id" AND c.rn = 1
)
SELECT "roadwork_id" AS roadwork_id, "street" AS street, "district_no" AS district_no, "district_name" AS district_name,
       status, "kind" AS kind, "impact" AS impact, "affected_areas" AS affected_areas, description,
       TO_CHAR("start_date", 'YYYY-MM-DD') AS start_date, "start_raw" AS start_raw, TO_CHAR("end_date", 'YYYY-MM-DD') AS end_date,
       days_in_window, closure, carriageway, "centroid_lat" AS lat, "centroid_lon" AS lon,
       stops_150m, departures_150m, nearest_stop, nearest_stop_m, lines_150m, hf_lines_150m, hf_lines,
       cycle_m_100m, cycle_street, bike_counter, counter_avg_daily, score
FROM scored
ORDER BY score DESC, departures_150m DESC
