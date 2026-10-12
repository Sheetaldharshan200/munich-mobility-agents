WITH
d AS (
    SELECT b."station", s."station_name", b."count_date", b."total", b."rain_mm", b."temp_max_c", b."sunshine_hours",
           CASE WHEN TO_CHAR(b."count_date", 'ID') IN ('6', '7') THEN 'weekend' ELSE 'weekday' END AS day_type,
           CASE WHEN b."rain_mm" <= 1 THEN 'dry' ELSE 'rainy' END AS wx
    FROM "MUNICH_DATASET".BIKE_COUNTS_DAILY b JOIN "MUNICH_DATASET".BIKE_COUNT_STATIONS s ON s."station" = b."station"
    WHERE b."total" IS NOT NULL
),

per AS (
    SELECT "station", "station_name", AVG("total") AS avg_daily,
           1 - AVG(CASE WHEN wx = 'rainy' THEN "total" END) / NULLIF(AVG(CASE WHEN wx = 'dry' THEN "total" END), 0) AS rain_penalty
    FROM d GROUP BY "station", "station_name"
)
SELECT (SELECT SUM("total") FROM d) AS cyclists_counted,
       (SELECT COUNT(DISTINCT "station") FROM d) AS counters,
       (SELECT TO_CHAR(MIN("count_date"), 'YYYY-MM-DD') FROM d) AS first_day,
       (SELECT TO_CHAR(MAX("count_date"), 'YYYY-MM-DD') FROM d) AS last_day,
       (SELECT "station_name" FROM per ORDER BY avg_daily DESC LIMIT 1) AS busiest_counter,
       (SELECT ROUND(avg_daily) FROM per ORDER BY avg_daily DESC LIMIT 1) AS busiest_avg_daily,
       (SELECT ROUND(AVG(rain_penalty), 2) FROM per) AS avg_rain_penalty,
       (SELECT ROUND(AVG(CASE WHEN wx = 'rainy' THEN "total" END) / NULLIF(AVG(CASE WHEN wx = 'dry' THEN "total" END), 0), 2) FROM d) AS rainy_vs_dry_ratio
FROM DUAL
