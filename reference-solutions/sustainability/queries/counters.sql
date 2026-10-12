WITH
d AS (
    SELECT b."station", s."station_name", b."count_date", b."total", b."rain_mm", b."temp_max_c", b."sunshine_hours",
           CASE WHEN TO_CHAR(b."count_date", 'ID') IN ('6', '7') THEN 'weekend' ELSE 'weekday' END AS day_type,
           CASE WHEN b."rain_mm" <= 1 THEN 'dry' ELSE 'rainy' END AS wx
    FROM "MUNICH_DATASET".BIKE_COUNTS_DAILY b JOIN "MUNICH_DATASET".BIKE_COUNT_STATIONS s ON s."station" = b."station"
    WHERE b."total" IS NOT NULL
),

stats AS (
    SELECT "station", "station_name", COUNT(*) AS days, MIN("count_date") AS first_day, MAX("count_date") AS last_day,
           SUM("total") AS total_cyclists, ROUND(AVG("total")) AS avg_daily,
           ROUND(AVG(CASE WHEN day_type = 'weekday' THEN "total" END)) AS avg_weekday,
           ROUND(AVG(CASE WHEN day_type = 'weekend' THEN "total" END)) AS avg_weekend,
           ROUND(AVG(CASE WHEN wx = 'dry' THEN "total" END)) AS avg_dry,
           ROUND(AVG(CASE WHEN wx = 'rainy' THEN "total" END)) AS avg_rainy,
           SUM(CASE WHEN wx = 'rainy' THEN 1 ELSE 0 END) AS rainy_days,
           ROUND(CORR("total", "sunshine_hours"), 2) AS corr_sunshine,
           ROUND(REGR_SLOPE("total", "temp_max_c"), 1) AS cyclists_per_degree
    FROM d GROUP BY "station", "station_name"
),
seq AS (
    SELECT "station", "count_date", "total", wx,
           AVG(CASE WHEN wx = 'dry' THEN "total" END) OVER (PARTITION BY "station" ORDER BY "count_date" ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS trailing_dry,
           LAG(wx) OVER (PARTITION BY "station" ORDER BY "count_date") AS prev_wx
    FROM d
),
recov AS (
    -- first dry day after a rainy day, relative to the trailing 7-day dry average
    SELECT "station", MEDIAN("total" / NULLIF(trailing_dry, 0)) AS recovery_ratio, COUNT(*) AS recovery_events
    FROM seq WHERE wx = 'dry' AND prev_wx = 'rainy' AND trailing_dry IS NOT NULL
    GROUP BY "station"
)
SELECT s."station" AS station, s."station_name" AS station_name, s.days, TO_CHAR(s.first_day, 'YYYY-MM-DD') AS first_day,
       TO_CHAR(s.last_day, 'YYYY-MM-DD') AS last_day, s.total_cyclists, s.avg_daily, s.avg_weekday, s.avg_weekend,
       ROUND(s.avg_weekday / NULLIF(s.avg_weekend, 0), 2) AS weekday_weekend_ratio,
       s.avg_dry, s.avg_rainy, s.rainy_days,
       ROUND(1 - s.avg_rainy / NULLIF(s.avg_dry, 0), 2) AS rain_penalty,
       s.corr_sunshine, s.cyclists_per_degree,
       ROUND(r.recovery_ratio, 2) AS recovery_ratio, r.recovery_events,
       RANK() OVER (ORDER BY r.recovery_ratio DESC NULLS LAST) AS recovery_rank
FROM stats s LEFT JOIN recov r ON r."station" = s."station"
ORDER BY s.avg_daily DESC
