SELECT c."district_no" AS district_no, d."district_name" AS district_name,
       CASE WHEN c."path_type" LIKE 'Getrennter%' THEN 'Separated cycle path'
            WHEN c."path_type" LIKE 'Radweg%' THEN 'Cycle path'
            WHEN c."path_type" LIKE 'Gemeinsamer%' THEN 'Shared path'
            WHEN c."path_type" LIKE 'Radfahr%' THEN 'Cycle lane'
            WHEN c."path_type" = 'Fahrradstraße' THEN 'Cycle street'
            WHEN c."path_type" LIKE 'Gehweg%' THEN 'Footway, cycling allowed'
            ELSE 'Other' END AS path_group,
       ROUND(SUM(c."length_m")) AS metres
FROM "MUNICH_DATASET".CYCLING_INFRASTRUCTURE c
JOIN "MUNICH_DATASET".DISTRICTS d ON d."district_no" = c."district_no"
WHERE c."path_type" <> 'Dummy'
GROUP BY c."district_no", d."district_name", 3
ORDER BY district_no, metres DESC
