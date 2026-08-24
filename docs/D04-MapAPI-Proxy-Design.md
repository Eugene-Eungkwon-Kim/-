# D04: 지도 API 키 프록시화 설계서

**작성일**: 2026-07-01  
**담당**: BE Lead + FE Lead  
**상태**: Design Review In Progress  
**목표**: 클라이언트에서 노출된 API 키를 백엔드 프록시로 마이그레이션

---

## 1. 현황 분석

### 1.1 문제점
- **API 키 노출**: 클라이언트(브라우저) JavaScript에서 카카오맵 API 키, VWorld API 키 직접 사용
  - grep 결과: `api_key=50D9ECCF-3977-37F1-B323-4997BEAAE387` (VWorld) 노출
  - 카카오맵 키도 마찬가지로 HTML/JS에 임베드
- **보안 리스크**: 악의적 사용자가 API 키를 탈취 → API 할당량 소진, 무단 위치 추적
- **규제 위반**: 금융감시규정상 "고객정보 제3자 노출 금지" 범위에 포함 가능

### 1.2 마이그레이션 대상
- 카카오맵 (`https://dapi.kakao.com/v2/maps/sdk.js?appkey=XXXX`)
- VWorld (`https://api.vworld.kr/req/data?key=XXXX`)
- 이후 확장: 네이버맵, Google Maps (동일 패턴)

---

## 2. 솔루션 아키텍처

### 2.1 구성도

```
┌──────────────┐                          ┌──────────────────────┐
│   Browser    │                          │   Reverse Proxy      │
│  (maars)     │                          │   (Node.js/Python)   │
└──────────────┘                          └──────────────────────┘
       │                                           │
       │  1. GET /api/v1/map/places               │
       │     {query, lat, lng}                    │
       │──────────────────────────────────────→  │
       │  (JWT 토큰 포함)                         │
       │                                          │
       │                                  2. 내부 검증
       │                                   - JWT 파싱 (사용자 ID)
       │                                   - 레이트리미팅 확인
       │                                   - 감사로그 기록
       │                                          │
       │                          3. 외부 API 호출
       │                          GET /dapi.kakao.com/v2/maps
       │                              ?query=X&appkey=SECRET
       │                                          │
       │  4. 응답 반환                            │
       │  {places: [...]}  ←──────────────────  │
       │                     (API 키 제거)
       │
```

### 2.2 엔드포인트 명세 (OpenAPI 3.0)

```yaml
openapi: 3.0.0
info:
  title: MAARS Map Proxy API
  version: '1.0.0'
  description: 지도 API 키를 서버에서 관리하는 프록시 레이어

servers:
  - url: https://api.maars.kr
    description: Production
  - url: http://localhost:3000
    description: Local Development

paths:
  /api/v1/map/places:
    get:
      summary: 지도 장소 검색 (카카오맵)
      tags:
        - Map
      security:
        - BearerAuth: []
      parameters:
        - name: query
          in: query
          required: true
          schema:
            type: string
            example: "강남역"
          description: 검색 키워드
        - name: lat
          in: query
          schema:
            type: number
            example: 37.4979
          description: 중심 위도 (선택사항)
        - name: lng
          in: query
          schema:
            type: number
            example: 127.0276
          description: 중심 경도 (선택사항)
        - name: radius
          in: query
          schema:
            type: integer
            default: 1000
          description: 검색 반경(미터)
      responses:
        '200':
          description: 성공
          content:
            application/json:
              schema:
                type: object
                properties:
                  places:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: string
                        name:
                          type: string
                        address:
                          type: string
                        lat:
                          type: number
                        lng:
                          type: number
                        category:
                          type: string
                          enum: [부동산, 관공서, 은행, 병원]
                    example:
                      - id: "kakao_place_123"
                        name: "강남역 부동산"
                        address: "서울시 강남구..."
                        lat: 37.4979
                        lng: 127.0276
                        category: "부동산"
                  meta:
                    type: object
                    properties:
                      totalCount:
                        type: integer
                      pageableCount:
                        type: integer
        '401':
          description: 인증 실패 (JWT 없음 또는 만료)
        '429':
          description: 요청 한도 초과 (레이트리미팅)
          headers:
            X-RateLimit-Limit:
              schema:
                type: integer
              description: 시간당 요청 한도
            X-RateLimit-Remaining:
              schema:
                type: integer
              description: 남은 요청 수

  /api/v1/map/vworld:
    get:
      summary: VWorld 공간 정보 조회
      tags:
        - Map
      security:
        - BearerAuth: []
      parameters:
        - name: dataType
          in: query
          required: true
          schema:
            type: string
            enum: [LT, AD, AM]
          description: |
            - LT: 지적도(부동산 경계)
            - AD: 행정경계
            - AM: 지형도
      responses:
        '200':
          description: 성공
          content:
            application/json:
              schema:
                type: object
                properties:
                  features:
                    type: array

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |
        JWT 토큰 (로그인 후 획득)
        Authorization: Bearer eyJhbGc...
```

---

## 3. 구현 사양

### 3.1 백엔드 구현 (Node.js/Express 예시)

#### 3.1.1 환경 변수 (.env)
```
KAKAO_MAP_API_KEY=xxxxx
VWORLD_API_KEY=50D9ECCF-3977-37F1-B323-4997BEAAE387
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key
```

#### 3.1.2 라우팅 (routes/map.js)
```javascript
// GET /api/v1/map/places
router.get('/places', authenticateJWT, rateLimit, async (req, res) => {
  const { query, lat, lng, radius } = req.query;
  const userId = req.user.id; // JWT에서 추출
  
  // 입력 검증
  if (!query) return res.status(400).json({ error: 'query required' });
  
  // 감시 로그 기록 (비동기, non-blocking)
  auditLog.record({
    userId,
    action: 'map_search',
    query,
    timestamp: new Date().toISOString(),
    status: 'pending'
  });
  
  try {
    // 캐시 확인 (Redis)
    const cacheKey = `map:places:${query}:${lat}:${lng}`;
    const cached = await redis.get(cacheKey);
    if (cached) {
      auditLog.update(cacheKey, { status: 'success', source: 'cache' });
      return res.json(JSON.parse(cached));
    }
    
    // 카카오 API 호출 (API 키는 서버에서만 사용)
    const kakaoRes = await fetch('https://dapi.kakao.com/v2/maps/search/geo', {
      headers: {
        'Authorization': `KakaoAK ${process.env.KAKAO_MAP_API_KEY}`
      },
      params: { query, x: lng, y: lat, radius }
    });
    
    const data = await kakaoRes.json();
    const places = data.documents.map(doc => ({
      id: `kakao_${doc.id}`,
      name: doc.place_name,
      address: doc.address_name,
      lat: parseFloat(doc.y),
      lng: parseFloat(doc.x),
      category: categorizePlace(doc.category_group_code)
    }));
    
    // 캐시 저장 (TTL: 1시간)
    await redis.setex(cacheKey, 3600, JSON.stringify({ places }));
    
    // 감시 로그 업데이트
    auditLog.update(cacheKey, { status: 'success', count: places.length });
    
    res.json({ places, meta: { totalCount: places.length } });
    
  } catch (error) {
    auditLog.update(cacheKey, { status: 'error', error: error.message });
    res.status(500).json({ error: 'Map API 호출 실패' });
  }
});
```

### 3.2 레이트리미팅 전략 (redis-based)

```javascript
// middleware/rateLimit.js
const rateLimit = async (req, res, next) => {
  const userId = req.user.id;
  const key = `ratelimit:${userId}`;
  
  const count = await redis.incr(key);
  if (count === 1) {
    await redis.expire(key, 3600); // 1시간 윈도우
  }
  
  const limit = 100; // 시간당 100건
  if (count > limit) {
    return res.status(429).json({
      error: 'Rate limit exceeded',
      retryAfter: await redis.ttl(key)
    });
  }
  
  res.setHeader('X-RateLimit-Limit', limit);
  res.setHeader('X-RateLimit-Remaining', limit - count);
  next();
};
```

### 3.3 감시 로그 스키마 (PostgreSQL)

```sql
CREATE TABLE audit_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  action VARCHAR(50) NOT NULL,
  resource_type VARCHAR(50),
  resource_id VARCHAR(255),
  details JSONB,
  status VARCHAR(20),
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ip_address INET,
  user_agent TEXT,
  
  INDEX idx_user_id_timestamp (user_id, timestamp),
  INDEX idx_action_timestamp (action, timestamp)
);

-- 예: 지도 검색 로그
INSERT INTO audit_logs 
  (user_id, action, resource_type, details, status, timestamp)
VALUES 
  ('user_123', 'map_search', 'location', 
   '{"query": "강남역", "lat": 37.4979, "result_count": 5}',
   'success', NOW());
```

---

## 4. 클라이언트 마이그레이션

### 4.1 기존 코드 (jQuery, 변경 전)
```javascript
// 변경 전: API 키가 클라이언트에 노출됨
const kakaoMapKey = '12345-XXXXXX'; // ❌ 노출
const map = new kakao.maps.Map(document.getElementById('map'), {
  center: new kakao.maps.LatLng(37.5, 126.9),
  level: 3
});

$('#search-btn').click(function() {
  const query = $('#search-input').val();
  
  // 직접 카카오 API 호출 (API 키 노출)
  fetch(`https://dapi.kakao.com/v2/maps/search/geo?query=${query}&appkey=${kakaoMapKey}`)
    .then(r => r.json())
    .then(data => {
      // 마커 추가
      data.documents.forEach(doc => {
        new kakao.maps.Marker({
          position: new kakao.maps.LatLng(doc.y, doc.x),
          title: doc.place_name,
          map: map
        });
      });
    });
});
```

### 4.2 신규 코드 (React, 변경 후)
```javascript
// 변경 후: 프록시를 통한 호출
const MapContainer = () => {
  const [places, setPlaces] = useState([]);
  const [query, setQuery] = useState('');
  const mapRef = useRef(null);
  
  const handleSearch = async () => {
    try {
      // ✅ 클라이언트에서는 프록시 호출만
      const res = await fetch('/api/v1/map/places', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${getJWT()}`,
          'Content-Type': 'application/json'
        },
        params: { query }
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      const { places } = await res.json();
      setPlaces(places);
      
      // 지도에 마커 추가
      places.forEach(place => {
        new kakao.maps.Marker({
          position: new kakao.maps.LatLng(place.lat, place.lng),
          title: place.name,
          map: mapRef.current
        });
      });
      
    } catch (error) {
      console.error('검색 실패:', error);
      alert('검색 중 오류가 발생했습니다.');
    }
  };
  
  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="검색어 입력"
      />
      <button onClick={handleSearch}>검색</button>
      <div ref={mapRef} style={{ width: '100%', height: '500px' }} />
    </div>
  );
};
```

---

## 5. 배포 & 전환 계획

### 5.1 배포 단계

| 단계 | 기간 | 대상 | 주요 작업 |
|------|------|------|---------|
| **설계 리뷰** | 2026-07-03 ~ 07-05 | BE/FE Lead | OpenAPI 명세 검토, 보안 감사 |
| **개발** | 2026-07-06 ~ 07-10 | BE 팀(1명) | 백엔드 프록시 구현, 테스트 |
| **통합테스트** | 2026-07-11 ~ 07-13 | FE + BE | 클라이언트 호출 테스트, 성능 측정 |
| **스테이징 배포** | 2026-07-14 | DevOps | 스테이징 환경에 배포, 모니터링 1일 |
| **프로덕션 배포** | 2026-07-15 | DevOps | 5% 카나리 → 50% → 100% (bluegreen) |

### 5.2 롤백 계획
- 프록시 상태 이상 감지 시 즉시 클라이언트에 구버전 서빙
- Git 태그: `v0.1.8-pre-proxy`, `v0.1.9-proxy-active` 유지
- 클라이언트 feature flag: `useMapProxy: true/false` (런타임 전환)

---

## 6. 검증 체크리스트

- [ ] OpenAPI 명세 FE/BE Lead 승인
- [ ] 백엔드 로컬 개발 환경에서 작동 확인
- [ ] 프록시 호출 시 API 키 grep 결과 = 0
- [ ] 레이트리미팅 동작 확인 (100건 초과 시 429 반환)
- [ ] 감시로그 5건 이상 기록 확인
- [ ] 스테이징 환경 성능 테스트: P95 응답시간 < 500ms
- [ ] 프로덕션 배포 후 모니터링 24시간 (에러율, 응답시간, API 할당량)
- [ ] 클라이언트 코드에서 "api_key", "appkey" 문자열 제거 확인

---

## 7. 향후 개선사항 (Phase 3+)

- GraphQL 레이어 추가 (REST 추상화 단순화)
- 지도 API 캐싱 전략 개선 (GeoHash 기반 버킷팅)
- WebSocket 실시간 위치 업데이트 (추적 기능)
- 멀티 클라우드 지원 (AWS CloudFront + 구글 클라우드 로드밸런싱)

---

**작성자**: Claude (Code Assistant)  
**검토 예정**: BE Lead, FE Lead, DevOps Lead  
**최종 승인**: Architecture Lead
