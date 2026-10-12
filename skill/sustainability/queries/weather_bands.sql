WITH
d AS (
    SELECT b."station", s."station_name", b."count_date", b."total", b."rain_mm", b."temp_max_c", b."sunshine_hours",
           CASE WHEN TO_CHAR(b."count_date", 'ID') IN ('6', '7') THEN 'weekend' ELSE 'weekday' END AS day_type,
           CASE WHEN b."rain_mm" <= 1 THEN 'dry' ELSE 'rainy' END AS wx
    FROM "MUNICH_DATASET".BIKE_COUNTS_DAILY b JOIN "MUNICH_DATASET".BIKE_COUNT_STATIONS s ON s."station" = b."station"
    WHERE b."total" IS NOT NULL
)
SELECT "station" AS station, "station_name" AS station_name,
       FLOOR("temp_max_c" / 5) * 5 AS temp_band_from, wx,
       ROUND(AVG("total")) AS avg_daily, COUNT(*) AS days
FROM d GROUP BY "station", "station_name", 3, wx ORDER BY station, temp_band_from, wx
