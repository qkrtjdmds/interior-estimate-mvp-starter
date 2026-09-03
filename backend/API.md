# Backend API

이 문서는 현재 백엔드 MVP API 계약을 요약합니다. Swagger 문서는 서버 실행 후 `http://127.0.0.1:8000/docs`에서 확인합니다.

## 공통

- Base URL: `http://127.0.0.1:8000`
- JSON API prefix: `/api`
- 관리자 인증: `Authorization: Bearer ADMIN_ACCESS_TOKEN`
- 공유 견적 인증: `X-Estimate-Share-Token: RAW_SHARE_TOKEN`
- 금액은 `Decimal` 기반으로 계산합니다.
- 견적 품목은 생성 시점의 Category, Item, Option 이름, 단위, 단가 snapshot을 저장합니다.

## Health

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| GET | `/` | 없음 | 서버 기본 응답 |
| GET | `/api/health` | 없음 | 서버 상태 확인 |
| GET | `/api/health/db` | 없음 | DB 연결 확인 |

## 고객 공개 API

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| GET | `/api/catalog` | 없음 | 고객 노출 기준정보 조회 |
| POST | `/api/estimates/preview` | 없음 | 선택 옵션과 수량으로 예상 금액 계산 |
| POST | `/api/estimates` | 없음 | 고객 견적 생성 |
| GET | `/api/public/estimate` | 공유 token header | 공유 견적 조회 |
| GET | `/api/public/estimate/pdf` | 공유 token header | 공유 견적 PDF 다운로드 |

고객 견적 흐름:

1. 이름, 연락처, 선택 이메일을 입력합니다. 프론트는 개인정보를 localStorage에 저장하지 않습니다.
2. 주거 형태, 평수, 시공 범위, 시공 지역, 희망 시기를 입력합니다.
3. `GET /api/catalog`로 고객 노출 기준정보를 조회합니다.
4. 원하는 시공 항목과 옵션, 수량을 선택합니다.
5. `POST /api/estimates/preview`로 예상 금액을 계산합니다.
6. 최종 확인 단계에서만 `POST /api/estimates`로 견적을 저장합니다.
7. 공유받은 고객은 raw token을 URL fragment로 받은 뒤 `X-Estimate-Share-Token` header로만 전송합니다.

## 견적 생성 요청 예

```json
{
  "customer_name": "홍길동",
  "customer_phone": "010-0000-0000",
  "customer_email": "hong@example.com",
  "housing_type": "아파트",
  "floor_area_pyeong": "32.50",
  "renovation_scope": "부분 인테리어",
  "preferred_timeline": "1개월 이내",
  "project_address": "서울 마포구",
  "notes": "우드톤을 원합니다.",
  "items": [
    {
      "option_id": 1,
      "quantity": "24.50",
      "sort_order": 1
    }
  ]
}
```

## 관리자 API

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | 없음 | 관리자 JWT 발급 |
| GET | `/api/auth/me` | 관리자 | 현재 관리자 확인 |
| POST | `/api/categories` | 관리자 | Category 생성 |
| GET | `/api/categories` | 관리자 | Category 목록 |
| GET | `/api/categories/{category_id}` | 관리자 | Category 단건 |
| PATCH | `/api/categories/{category_id}` | 관리자 | Category 수정 |
| DELETE | `/api/categories/{category_id}` | 관리자 | 하위 Item이 없을 때 삭제 |
| POST | `/api/items` | 관리자 | Item 생성 |
| GET | `/api/items` | 관리자 | Item 목록 |
| GET | `/api/items/{item_id}` | 관리자 | Item 단건 |
| PATCH | `/api/items/{item_id}` | 관리자 | Item 수정 |
| DELETE | `/api/items/{item_id}` | 관리자 | 하위 Option이 없을 때 삭제 |
| POST | `/api/options` | 관리자 | Option 생성 |
| GET | `/api/options` | 관리자 | Option 목록 |
| GET | `/api/options/{option_id}` | 관리자 | Option 단건 |
| PATCH | `/api/options/{option_id}` | 관리자 | Option 수정 |
| DELETE | `/api/options/{option_id}` | 관리자 | Option 삭제 |
| GET | `/api/estimates` | 관리자 | 견적 목록 |
| GET | `/api/estimates/{estimate_id}` | 관리자 | 견적 단건 |
| PATCH | `/api/estimates/{estimate_id}` | 관리자 | 견적 정보 또는 상태 수정 |
| PUT | `/api/estimates/{estimate_id}/items` | 관리자 | draft 견적 품목 전체 교체 |
| POST | `/api/estimates/{estimate_id}/share` | 관리자 | 공유 링크 raw token 1회 발급 |
| GET | `/api/estimates/{estimate_id}/share` | 관리자 | 현재 공유 링크 상태 조회 |
| DELETE | `/api/estimates/{estimate_id}/share` | 관리자 | 현재 공유 링크 폐기 |
| GET | `/api/estimates/{estimate_id}/pdf` | 관리자 | 관리자용 PDF 다운로드 |

## 공개 개인정보 정책

`GET /api/public/estimate`와 `GET /api/public/estimate/pdf`는 공개 공유 범위만 제공합니다. 연락처, 이메일, 상세 주소, 요청사항, 내부 id, token hash는 공개 응답에 포함하지 않습니다.

## 오류 응답

| 상태 코드 | 의미 |
| --- | --- |
| 400 | 상태 전이 실패, 잘못된 업무 요청 |
| 401 | 인증 정보 없음 또는 유효하지 않음 |
| 403 | 비활성 관리자 계정 |
| 404 | 리소스 없음 또는 공개 공유 조회 불가 |
| 409 | 중복 데이터, 하위 데이터가 있는 삭제 요청, 사용할 수 없는 옵션 |
| 410 | 공유 링크 만료 |
| 422 | 입력값 검증 실패 |
| 503 | PDF 한글 폰트 미설정 등 서비스 준비 실패 |

오류 응답에는 DB 접속 정보, SQL 상세 정보, 비밀번호, token 원문을 포함하지 않습니다.
