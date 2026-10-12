SELECT b."station" AS station, s."station_name" AS station_name, TO_CHAR(b."count_date", 'YYYY-MM-DD') AS count_date,
       b."total" AS total, b."rain_mm" AS rain_mm, b."temp_max_c" AS temp_max_c
FROM "MUNICH_DATASET".BIKE_COUNTS_DAILY b JOIN "MUNICH_DATASET".BIKE_COUNT_STATIONS s ON s."station" = b."station"
ORDER BY b."count_date", b."station"
