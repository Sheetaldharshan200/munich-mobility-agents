SELECT f."station" AS station, s."station_name" AS station_name,
       TO_CHAR(f."count_date", 'ID') AS iso_weekday, TO_NUMBER(SUBSTR(f."time_start", 1, 2)) AS hour_of_day,
       ROUND(SUM(f."total") / COUNT(DISTINCT f."count_date"), 1) AS avg_cyclists_per_hour
FROM "MUNICH_DATASET".BIKE_COUNTS_15MIN f JOIN "MUNICH_DATASET".BIKE_COUNT_STATIONS s ON s."station" = f."station"
GROUP BY f."station", s."station_name", 3, 4
ORDER BY station, iso_weekday, hour_of_day
