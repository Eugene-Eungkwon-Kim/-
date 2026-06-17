-- =============================================================
-- 1순위: 화면 마트 미반영 596건 즉시 백필
-- 원인: 마트 동기화가 PNU 기반 조인을 써서 pnu=NULL인 건축물링크 면적을 누락
-- 조치: energy_site_id 기반 조인으로 변경
-- 멱등: 이미 채워진 건은 건드리지 않음 (AND m.station_site_area_m2 IS NULL)
-- =============================================================

BEGIN;

-- 1-A. 백필 실행
UPDATE energy_site_search_mart m
SET
    station_site_area_m2 = s.total_land_area_m2,
    area_source          = s.area_source,
    area_updated_at      = NOW()
FROM energy_site_land_area_summary s
WHERE m.energy_site_id = s.energy_site_id           -- PNU가 아닌 안정 키
  AND s.value_status = 'READY'
  AND s.total_land_area_m2 IS NOT NULL
  AND s.total_land_area_m2 > 0
  AND (m.station_site_area_m2 IS NULL OR m.station_site_area_m2 = 0);

-- 1-B. 결과 확인 (기대값: rows_updated ≒ 596)
SELECT
    COUNT(*) FILTER (WHERE station_site_area_m2 IS NOT NULL AND station_site_area_m2 > 0) AS mart_shown_after,
    COUNT(*) FILTER (WHERE station_site_area_m2 IS NULL OR station_site_area_m2 = 0)      AS mart_blank_after
FROM energy_site_search_mart;

COMMIT;


-- =============================================================
-- 재발 방지: 마트 빌드 잡 수정 참고 쿼리
-- 기존 잡에서 아래 패턴으로 변경할 것
-- Before: JOIN energy_site_land_area_summary s ON m.pnu = s.pnu
-- After:  JOIN energy_site_land_area_summary s ON m.energy_site_id = s.energy_site_id
-- =============================================================

-- 재발 방지 전체 동기화 (배치 잡 교체용)
UPDATE energy_site_search_mart m
SET
    station_site_area_m2 = s.total_land_area_m2,
    area_source          = s.area_source,
    area_updated_at      = NOW()
FROM energy_site_land_area_summary s
WHERE m.energy_site_id = s.energy_site_id
  AND s.value_status = 'READY'
  AND s.total_land_area_m2 IS NOT NULL
  AND s.total_land_area_m2 > 0;
