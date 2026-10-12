SELECT s."station" AS station, s."station_name" AS station_name, s."lat" AS lat, s."lon" AS lon,
       d."district_name" AS district_name, s."direction_1" AS direction_1, s."direction_2" AS direction_2,
       ROUND(AVG(b."total")) AS avg_daily, COUNT(b."count_date") AS days
FROM "MUNICH_DATASET".BIKE_COUNT_STATIONS s
LEFT JOIN "MUNICH_DATASET".DISTRICTS d ON d."district_no" = s."district_no"
LEFT JOIN "MUNICH_DATASET".BIKE_COUNTS_DAILY b ON b."station" = s."station"
GROUP BY s."station", s."station_name", s."lat", s."lon", d."district_name", s."direction_1", s."direction_2"
ORDER BY avg_daily DESC NULLS LAST
