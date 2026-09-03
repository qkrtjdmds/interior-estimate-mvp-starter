# Backend API

이 문서는 현재 백엔드 MVP API 계약을 요약합니다. Swagger 문서는 서버 실행 후 `http://127.0.0.1:8000/docs`에서 확인합니다.

## 공통

- Base URL: `http://127.0.0.1:8000`
- JSON API prefix: `/api`
- 관리자 인증: `Authorization: Bearer ADMIN_ACCESS_TOKEN`
- 공유 견적 인증: `X-Estimate-Share-Token: RAW_SHARE_TOKEN`
- 금액은 `Decimal` 기반으로 계산하고 응답에서는 안정적인 JSON 숫자 또는 문자열 형식으로 직렬화합니다.
- 견적은 생성 시점의 Category, Item, Option 이름, 단위, 단가 snapshot을 저장합니다. 이후 기준 단가가 바뀌어도 기존 견적 금액은 바뀌지 않습니다.

## Health

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| GET | `/` | 없음 | 서버 기본 응답 |
| GET | `/api/health` | 없음 | 서버 상태 확인 |
| GET | `/api/health/db` | 없음 | DB 연결 확인 |

## Auth

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | 없음 | 관리자 이메일/비밀번호로 JWT 발급 |
| GET | `/api/auth/me` | 관리자 | 현재 관리자 계정 확인 |

로그인 성공 응답에는 access token이 포함됩니다. 토큰은 로그나 URL에 남기지 않습니다.

## 고객 공개 API

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| GET | `/api/catalog` | 없음 | customer_visible 기준 Category, Item, Option 목록 |
| POST | `/api/estimates/preview` | 없음 | 선택 옵션과 수량으로 예상 금액 계산 |
| POST | `/api/estimates` | 없음 | 고객 견적 생성 |
| GET | `/api/public/estimate` | 공유 token header | 공유 견적 조회 |
| GET | `/api/public/estimate/pdf` | 공유 token header | 공유 견적 PDF 다운로드 |

공유 API는 raw token을 path 또는 query string으로 받지 않습니다. 항상 `X-Estimate-Share-Token` header를 사용합니다.

## 기준정보 관리자 API

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| POST | `/api/categories` | 관리자 | Category 생성 |
| GET | `/api/categories` | 관리자 | Category 목록 |
| GET | `/api/categories/{category_id}` | 관리자 | Category 단건 |
| PATCH | `/api/categories/{category_id}` | 관리자 | Category 부분 수정 |
| DELETE | `/api/categories/{category_id}` | 관리자 | 하위 Item이 없을 때 실제 삭제 |
| POST | `/api/items` | 관리자 | Item 생성 |
| GET | `/api/items` | 관리자 | Item 목록 |
| GET | `/api/items/{item_id}` | 관리자 | Item 단건 |
| PATCH | `/api/items/{item_id}` | 관리자 | Item 부분 수정 |
| DELETE | `/api/items/{item_id}` | 관리자 | 하위 Option이 없을 때 실제 삭제 |
| POST | `/api/options` | 관리자 | Option 생성 |
| GET | `/api/options` | 관리자 | Option 목록 |
| GET | `/api/options/{option_id}` | 관리자 | Option 단건 |
| PATCH | `/api/options/{option_id}` | 관리자 | Option 부분 수정 |
| DELETE | `/api/options/{option_id}` | 관리자 | Option 실제 삭제 |

목록 API는 `skip`, `limit`, `name`, `active`, `customer_visible` 필터를 지원합니다. Item은 `category_id`, Option은 `item_id`, `recommended`, `unit` 필터를 추가로 지원합니다. 정렬은 `sort_order ASC, id ASC`입니다.

삭제 정책:

- Category에 Item이 있으면 `409 Conflict`
- Item에 Option이 있으면 `409 Conflict`
- 비활성화는 `PATCH active=false`로 처리

중복 정책:

- Category: `lower(btrim(name))`
- Item: `category_id + lower(btrim(name))`
- Option: `item_id + lower(btrim(name))`

애플리케이션 레벨 409 처리와 PostgreSQL functional unique index를 함께 사용합니다.

## 견적 관리자 API

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| GET | `/api/estimates` | 관리자 | 견적 목록 |
| GET | `/api/estimates/{estimate_id}` | 관리자 | 견적 단건 |
| PATCH | `/api/estimates/{estimate_id}` | 관리자 | 고객 정보, 메모, 상태 수정 |
| PUT | `/api/estimates/{estimate_id}/items` | 관리자 | draft 견적 품목 전체 교체 |
| POST | `/api/estimates/{estimate_id}/share` | 관리자 | 공유 링크 raw token 1회 발급 |
| GET | `/api/estimates/{estimate_id}/share` | 관리자 | 현재 공유 링크 상태 조회 |`r`n| DELETE | `/api/estimates/{estimate_id}/share` | 관리자 | 현재 공유 링크 폐기 |
| GET | `/api/estimates/{estimate_id}/pdf` | 관리자 | 관리자용 PDF 다운로드 |

상태 전이는 API에서 검증합니다. 공유 링크는 견적이 취소되면 공개 조회와 공개 PDF가 차단됩니다.

## 고객 견적 생성 예

```json
{
  "customer_name": "홍길동",
  "customer_phone": "010-0000-0000",
  "customer_address": "서울시",
  "items": [
    {
      "option_id": 1,
      "quantity": "24.5"
    }
  ]
}
```

`option_id`로 현재 기준정보를 조회한 뒤 견적 품목에는 당시 이름, 단위, 단가를 snapshot으로 저장합니다.

## 오류 응답

| 상태 코드 | 의미 |
| --- | --- |
| 400 | 상태 전이 실패, 잘못된 업무 요청 |
| 401 | 인증 정보 없음 또는 유효하지 않음 |
| 403 | 비활성 관리자 계정 |
| 404 | 리소스 없음 또는 공개 공유 조회 불가 |
| 409 | 중복 데이터, 하위 데이터가 있는 삭제 요청 |
| 410 | 공유 링크 만료 |
| 422 | Pydantic 입력값 검증 실패 |
| 503 | PDF 한글 폰트 미설정 등 서비스 준비 실패 |

오류 응답에는 DB 접속 정보, SQL 상세 정보, 비밀번호, token 원문을 포함하지 않습니다.

