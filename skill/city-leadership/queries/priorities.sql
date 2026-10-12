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
    SELECT rw."roadwork_id", stp."stop_id", stp."stop_name", stp.departures,
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
agg_stop AS (
    SELECT "roadwork_id", COUNT(*) AS stops_150m, SUM(departures) AS departures_150m, MIN(dist_m) AS nearest_stop_m
    FROM near_stop GROUP BY "roadwork_id"
),
nearest AS (
    SELECT "roadwork_id", "stop_name" AS nearest_stop
    FROM (SELECT "roadwork_id", "stop_name", ROW_NUMBER() OVER (PARTITION BY "roadwork_id" ORDER BY dist_m) AS rn FROM near_stop) x
    WHERE rn = 1
),
agg_seg AS (
    SELECT "roadwork_id", SUM("length_m") AS cycle_m_100m FROM near_seg GROUP BY "roadwork_id"
),
scored AS (
    SELECT rw."roadwork_id", rw."street", rw."district_no", rw."kind", rw."impact", rw."affected_areas", rw.description,
           rw."start_date", rw."start_raw", rw."end_date", rw."centroid_lat", rw."centroid_lon", rw.status,
           rw.closure, rw.carriageway, rw.days_in_window, dd."district_name",
           COALESCE(a.stops_150m, 0) AS stops_150m, COALESCE(a.departures_150m, 0) AS departures_150m,
           ROUND(a.nearest_stop_m) AS nearest_stop_m, n.nearest_stop,
           ROUND(COALESCE(s.cycle_m_100m, 0)) AS cycle_m_100m,
           ROUND((LN(1 + COALESCE(a.departures_150m, 0)) + COALESCE(s.cycle_m_100m, 0) / 100
                  + 2 * rw.closure + rw.carriageway) * LEAST(rw.days_in_window, 28) / 28, 2) AS score
    FROM rw
    LEFT JOIN "MUNICH_DATASET".DISTRICTS dd ON dd."district_no" = rw."district_no"
    LEFT JOIN agg_stop a ON a."roadwork_id" = rw."roadwork_id"
    LEFT JOIN nearest n ON n."roadwork_id" = rw."roadwork_id"
    LEFT JOIN agg_seg s ON s."roadwork_id" = rw."roadwork_id"
),
ops AS (
    SELECT "district_no", SUM(score) AS disruption, COUNT(*) AS roadworks,
           SUM(CASE WHEN stops_150m > 0 THEN 1 ELSE 0 END) AS roadworks_near_stop
    FROM scored WHERE "district_no" IS NOT NULL GROUP BY "district_no"
),
demand AS (
    SELECT s."district_no", AVG(b."total") AS avg_daily_cyclists
    FROM "MUNICH_DATASET".BIKE_COUNTS_DAILY b JOIN "MUNICH_DATASET".BIKE_COUNT_STATIONS s ON s."station" = b."station"
    GROUP BY s."district_no"
),
ev_tab AS (
    SELECT g."district_no", g."district_name", g."population", g."density_per_ha", g.dep_per_1k, g.cycle_m_per_1k,
           g.density_idx, g.transit_idx, g.cycle_idx, g.flagged, g.flag_reason,
           COALESCE(o.disruption, 0) AS disruption, COALESCE(o.roadworks, 0) AS roadworks, COALESCE(o.roadworks_near_stop, 0) AS roadworks_near_stop,
           dm.avg_daily_cyclists
    FROM gap g LEFT JOIN ops o ON o."district_no" = g."district_no" LEFT JOIN demand dm ON dm."district_no" = g."district_no"
),
pr AS (
    SELECT e.*,
           100 - ROUND((e.transit_idx + e.cycle_idx) / 2.0) AS coverage_gap_idx,
           ROUND(100.0 * e.disruption / NULLIF(MAX(e.disruption) OVER (), 0)) AS disruption_idx,
           COALESCE(ROUND(100.0 * e.avg_daily_cyclists / NULLIF(MAX(e.avg_daily_cyclists) OVER (), 0)), 0) AS demand_idx
    FROM ev_tab e
),
prio AS (
    SELECT p.*,
           ROUND({w_density!f} * density_idx + {w_gap!f} * coverage_gap_idx + {w_disruption!f} * disruption_idx + {w_demand!f} * demand_idx, 1) AS priority,
           RANK() OVER (ORDER BY {w_density!f} * density_idx + {w_gap!f} * coverage_gap_idx + {w_disruption!f} * disruption_idx + {w_demand!f} * demand_idx DESC) AS priority_rank
    FROM pr p
)
SELECT "district_no" AS district_no, "district_name" AS district_name, "population" AS population,
       "density_per_ha" AS density_per_ha, dep_per_1k, cycle_m_per_1k, roadworks, roadworks_near_stop,
       ROUND(disruption, 1) AS disruption, ROUND(avg_daily_cyclists) AS avg_daily_cyclists,
       density_idx, coverage_gap_idx, disruption_idx, demand_idx, priority, priority_rank, flagged, flag_reason
FROM prio ORDER BY priority_rank
