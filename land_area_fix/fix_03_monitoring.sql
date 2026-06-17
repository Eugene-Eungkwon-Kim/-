-- =============================================================
-- 상시 모니터링: 요약 테이블 READY 건수 vs 마트 표시 건수 gap 감지
-- 일배치로 실행, gap > 0 이면 알림 발송
-- =============================================================

WITH counts AS (
    SELECT
        (SELECT COUNT(*)
         FROM energy_site_land_area_summary
         WHERE value_status = 'READY'
           AND total_land_area_m2 IS NOT NULL
           AND total_land_area_m2 > 0
        ) AS summary_ready,

        (SELECT COUNT(*)
         FROM energy_site_search_mart
         WHERE station_site_area_m2 IS NOT NULL
           AND station_site_area_m2 > 0
        ) AS mart_shown,

        (SELECT COUNT(*) FROM energy_site_search_mart) AS total_sites
)
SELECT
    summary_ready,
    mart_shown,
    total_sites,
    summary_ready - mart_shown AS gap,              -- 0이어야 정상
    ROUND(mart_shown::numeric / total_sites * 100, 1) AS display_rate_pct,
    CASE WHEN summary_ready - mart_shown > 0
         THEN '⚠️ 마트 동기화 누락 ' || (summary_ready - mart_shown) || '건 — 백필 SQL 재실행 필요'
         ELSE '✅ 정상 (gap = 0)'
    END AS status
FROM counts;


-- =============================================================
-- 미표시 사유 현황 (수시 점검용)
-- =============================================================

SELECT
    CASE
        WHEN s.value_status = 'NO_PNU'          THEN 'NO_PNU_OR_LAND_LINK'
        WHEN s.value_status = 'SOURCE_NOT_LOADED' THEN 'PNU_EXISTS_BUT_NO_LAND_AREA_SUMMARY'
        WHEN s.value_status = 'READY'
             AND (m.station_site_area_m2 IS NULL OR m.station_site_area_m2 = 0)
                                                 THEN 'LAND_SUMMARY_READY_BUT_SEARCH_MART_BLANK'
        ELSE 'OTHER_REVIEW_REQUIRED'
    END                          AS reason_code,
    e.site_category,
    e.source_provider,
    COUNT(*)                     AS site_count
FROM energy_site e
LEFT JOIN energy_site_land_area_summary s ON e.energy_site_id = s.energy_site_id
LEFT JOIN energy_site_search_mart m       ON e.energy_site_id = m.energy_site_id
WHERE m.station_site_area_m2 IS NULL OR m.station_site_area_m2 = 0
GROUP BY 1, 2, 3
ORDER BY site_count DESC;
