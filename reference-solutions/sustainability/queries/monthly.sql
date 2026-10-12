WITH
d AS (
    SELECT b."station", s."station_name", b."count_date", b."total", b."rain_mm", b."temp_max_c", b."sunshine_hours",
           CASE WHEN TO_CHAR(b."count_date", 'ID') IN ('6', '7') THEN 'weekend' ELSE 'weekday' END AS day_type,
           CASE WHEN b."rain_mm" <= 1 THEN 'dry' ELSE 'rainy' END AS wx
    FROM "MUNICH_DATASET".BIKE_COUNTS_DAILY b JOIN "MUNICH_DATASET".BIKE_COUNT_STATIONS s ON s."station" = b."station"
    WHERE b."total" IS NOT NULL
)
SELECT "station" AS station, "station_name" AS station_name, TO_CHAR("count_date", 'YYYY-MM') AS month_key,
       SUM("total") AS cyclists, ROUND(AVG("total")) AS avg_daily, COUNT(*) AS days,
       ROUND(AVG("temp_max_c"), 1) AS avg_temp_max, ROUND(SUM("rain_mm"), 1) AS rain_mm
FROM d GROUP BY "station", "station_name", 3 ORDER BY month_key, station
