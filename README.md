# Interior Estimate MVP Starter

인테리어 견적 자동화 웹서비스 MVP입니다. 현재 백엔드는 기준정보 관리, 고객 견적 생성, 관리자 견적 관리, 보안 공유 링크, 한국어 PDF 생성까지 구현되어 있습니다.

## 기술 스택

- Frontend: React, Vite, TypeScript
- Backend: FastAPI, SQLAlchemy 2.x, Pydantic v2
- Database: PostgreSQL 17
- Migration: Alembic
- Auth: JWT Bearer token, Argon2 password hash
- PDF: ReportLab

## 프로젝트 구조

```text
backend/
  alembic/                 # DB migration
  app/
    api/                   # FastAPI routers
    core/                  # settings, security
    crud/                  # DB query/write layer
    db/                    # session, seed, admin utility
    models/                # SQLAlchemy models
    schemas/               # Pydantic schemas
    services/              # price calculation, PDF generation
  tests/                   # backend tests
frontend/
  src/                     # Vite frontend source
```

## 로컬 설정

### 1. Backend 가상환경

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 환경 변수

`backend/.env.example`을 참고해서 `backend/.env`를 만듭니다. 실제 비밀번호, JWT secret, DB URL은 Git에 커밋하지 않습니다.

필수 항목:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/interior_estimate
JWT_SECRET_KEY=replace-with-a-long-random-secret-at-least-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480
```

PDF에 한글을 안정적으로 출력하려면 한국어 TTF 폰트 경로를 지정합니다.

```env
PDF_FONT_PATH=path-to-korean-regular-ttf
PDF_FONT_BOLD_PATH=path-to-korean-bold-ttf
```

Windows 개발 환경에서는 설치된 한국어 글꼴을 사용할 수 있습니다. Linux 배포 환경에서는 Noto Sans CJK KR 또는 Noto Sans KR 같은 한국어 폰트를 별도로 설치하고 경로를 지정합니다.

### 3. PostgreSQL

PostgreSQL에 `interior_estimate` DB를 준비합니다. 실제 계정과 비밀번호는 `.env`에만 둡니다.

### 4. Migration

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

새 migration 생성:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
```

개발 환경에서만 신중하게 downgrade를 사용합니다.

```powershell
.\.venv\Scripts\python.exe -m alembic downgrade -1
```

### 5. 기준정보 seed

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.db.seed_reference_data
```

Seed는 Category -> Item -> Option 순서로 저장합니다. 이름과 부모 관계 기준으로 기존 데이터를 재사용하므로 반복 실행해도 중복 데이터가 생성되지 않습니다.

### 6. 관리자 계정 생성

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.db.create_admin
```

비밀번호는 Argon2 hash로 저장됩니다. 운영 환경에서는 안전한 비밀번호와 별도 계정 관리 절차를 사용합니다.

### 7. FastAPI 실행

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

### 8. Frontend 실행

```powershell
cd frontend
npm install
npm run dev
```

Frontend dev server는 기본적으로 http://localhost:5173 에서 실행됩니다.

## 주요 API 흐름

상세 API 계약은 [backend/API.md](backend/API.md)를 확인합니다.

고객 견적 흐름:

1. 개인정보를 입력합니다. 이름과 연락처는 필수이며 새로고침 복구용 localStorage에 저장하지 않습니다.
2. 주거 형태, 평수, 시공 범위, 시공 지역, 희망 시기를 입력합니다.
3. 원하는 시공 항목을 선택합니다.
4. 항목별 옵션과 수량을 입력하고 POST /api/estimates/preview 결과로 예상 금액을 확인합니다.
5. 추가 요청사항과 전체 내용을 확인한 뒤 POST /api/estimates로 견적을 생성합니다.
6. 공유받은 고객은 raw token을 URL fragment로 받은 뒤 X-Estimate-Share-Token header로만 전송합니다.

관리자 흐름:

1. `POST /api/auth/login`으로 JWT access token을 발급받습니다.
2. `Authorization: Bearer <token>` header로 관리자 API를 호출합니다.
3. 기준정보 CRUD, 견적 조회/수정, 공유 링크 발급, PDF 다운로드를 수행합니다.

## 보안 공유 링크 규칙

공유 링크의 raw token은 URL path나 query string에 넣지 않습니다. 프론트엔드는 fragment로 받은 뒤 즉시 주소창에서 제거하고, API 호출 시 header로만 전송합니다.

```text
https://frontend.example/estimate/share#token=RAW_TOKEN
```

```http
GET /api/public/estimate
X-Estimate-Share-Token: RAW_SHARE_TOKEN
```

백엔드는 SHA-256 token hash만 저장합니다. raw token은 `POST /api/estimates/{estimate_id}/share` 응답에서 한 번만 반환됩니다.

## PDF 생성

PDF는 요청 시 메모리에서 생성되고 DB나 로컬 파일에 저장되지 않습니다.

관리자 PDF:

```http
GET /api/estimates/{estimate_id}/pdf
Authorization: Bearer ADMIN_ACCESS_TOKEN
```

공유 PDF:

```http
GET /api/public/estimate/pdf
X-Estimate-Share-Token: RAW_SHARE_TOKEN
```

관리자 PDF에는 고객 정보가 포함될 수 있고, 공개 공유 PDF는 고객 이름을 마스킹하며 전화번호, 주소, 요청사항을 제외합니다.

## 테스트

```powershell
cd backend
.\.venv\Scripts\python.exe -m compileall -q app tests alembic
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m alembic current
```

테스트는 개발 DB 전체를 삭제하지 않도록 구성되어 있습니다. 실제 DB 통합 smoke test는 임시 관리자, 임시 견적, 임시 공유 데이터만 만들고 정리합니다.

## Git 제외 대상

`.env`, `backend/.env`, 가상환경, 캐시, 빌드 결과, 로그, 로컬 DB 데이터, 임시 파일은 Git에 포함하지 않습니다. 비밀값 없는 `.env.example`은 커밋할 수 있습니다.
