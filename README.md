# Interior Estimate MVP Starter

인테리어 견적 자동화 웹서비스 MVP입니다. 고객 견적 작성, 관리자 견적 관리, 관리자 카탈로그 관리, 공유 링크, PDF 생성까지 구현되어 있습니다.

## 기술 스택

- Frontend: React, Vite, TypeScript
- Backend: FastAPI, SQLAlchemy 2.x, Pydantic v2
- Database: PostgreSQL
- Migration: Alembic
- Auth: JWT Bearer token, Argon2 password hash
- PDF: ReportLab

## 실행 구조

```text
frontend/
  src/                 # React source
  dist/                # npm run build 결과물, Git 제외
  vercel.json          # Vercel SPA fallback rewrite
backend/
  app/                 # FastAPI application
  alembic/             # DB migrations
  tests/               # pytest tests
```

프론트엔드는 `npm run build` 실행 시 `frontend/dist`에 정적 파일을 생성합니다. Vite 기본 출력 경로를 사용합니다.
백엔드는 `backend` 디렉터리에서 `python -m uvicorn app.main:app` 방식으로 실행합니다.

## 로컬 개발

### Backend

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`backend/.env`에는 실제 값을 넣습니다. 실제 DB 비밀번호, JWT secret, 토큰은 Git에 커밋하지 않습니다.

필수 환경변수:

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB_NAME
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
JWT_SECRET_KEY=replace-with-a-long-random-secret-at-least-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480
PDF_FONT_PATH=/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf
PDF_FONT_BOLD_PATH=/usr/share/fonts/truetype/noto/NotoSansKR-Bold.ttf
```

DB migration:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

기준정보 seed:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.db.seed_reference_data
```

관리자 계정 생성:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.db.create_admin --email admin@example.com
```

비밀번호는 터미널 프롬프트에서 입력하며 코드나 문서에 저장하지 않습니다.

서버 실행:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

- `GET /api/health`: 서버 프로세스 확인
- `GET /api/health/db`: DB 연결 확인

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

`frontend/.env` 예시:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_FRONTEND_BASE_URL=http://localhost:5173
```

프론트 API 주소는 `VITE_API_BASE_URL`로 설정합니다. 공유 링크 생성에 쓰는 프론트 기준 URL은 `VITE_FRONTEND_BASE_URL`로 설정하며, 없으면 현재 브라우저 origin을 사용합니다.

## 운영 배포 준비

### 환경변수

Backend 운영 환경에는 최소한 다음 값을 설정합니다.

- `APP_ENV=production`
- `DATABASE_URL`: 운영 PostgreSQL 접속 URL
- `CORS_ORIGINS`: 프론트 운영 도메인만 쉼표로 구분해 지정
- `JWT_SECRET_KEY`: 충분히 긴 난수 secret
- `JWT_ALGORITHM`: 기본 `HS256`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: 운영 정책에 맞는 만료 시간
- `PDF_FONT_PATH`, `PDF_FONT_BOLD_PATH`: 한글 출력 가능한 TTF/TTC 폰트 경로

Frontend 운영 환경에는 다음 값을 설정합니다.

- `VITE_API_BASE_URL`: 백엔드 API HTTPS URL
- `VITE_FRONTEND_BASE_URL`: 프론트 운영 HTTPS URL

### CORS

운영에서는 `APP_ENV=production`으로 실행합니다. 이 모드에서는 `CORS_ORIGINS`에 `https://` 운영 도메인만 허용됩니다. `localhost`, `127.0.0.1`, 사설 IP, `http://`, `*`가 들어 있으면 서버 시작 시 실패합니다.

```env
APP_ENV=production
CORS_ORIGINS=https://interior.example.com
```

### PDF

PDF는 요청 시 메모리에서 생성하며 로컬 파일로 저장하지 않습니다. 운영 Linux 환경에서는 Noto Sans KR 또는 Noto Sans CJK 계열 폰트를 설치하고 `PDF_FONT_PATH`, `PDF_FONT_BOLD_PATH`를 지정합니다. 폰트가 없으면 PDF API는 `503`을 반환합니다.

### 공유 링크와 HTTPS

공유 링크 원문 token은 URL fragment(`#token=...`)로 전달하고 API에는 `X-Estimate-Share-Token` header로만 전송합니다. 운영에서는 프론트와 백엔드 모두 HTTPS를 사용해야 합니다.

### SPA 라우팅

React Router를 사용하는 SPA입니다. 정적 호스팅에서 `/admin/estimates/1`, `/share` 같은 경로를 새로고침해도 `index.html`로 fallback되도록 설정해야 합니다. Vercel은 `frontend/vercel.json`에 rewrite가 포함되어 있습니다.

### 파일 업로드와 정적 파일

현재 코드 기준으로 사용자 파일 업로드 기능과 백엔드 정적 파일 서빙은 없습니다. 프론트 정적 파일은 호스팅 서비스가 `frontend/dist`를 서빙합니다.

### 로그와 민감정보

API 오류 응답은 DB 접속정보, 비밀번호, JWT, 공유 token 원문을 반환하지 않도록 구성되어 있습니다. 운영 호스팅 로그에도 실제 요청 header와 body 전체를 남기지 않는 설정을 유지해야 합니다.

## 추천 배포 방식

2026-09-04 기준 공개 가격 페이지를 확인한 대략치입니다. 결제 전 최신 가격과 무료 플랜 제한을 다시 확인합니다.

### 1순위: Vercel + Render 또는 Railway + Managed PostgreSQL

- 비용: 프론트는 Vercel Hobby 무료로 시작 가능. 상업/팀 운영은 Vercel Pro가 월 $20부터입니다. 백엔드와 PostgreSQL은 Render/Railway의 무료 또는 저가 플랜으로 시작할 수 있으나, DB 지속성/리소스/콜드 스타트 제한을 반드시 확인해야 합니다.
- 장점: 초보자가 HTTPS, 빌드, 로그, 환경변수, Git 연동을 다루기 쉽습니다. 프론트와 백엔드 장애 범위가 분리됩니다.
- 단점: 무료/저가 플랜은 sleep, cold start, 리소스 제한, DB 용량 제한이 있을 수 있습니다. 서비스가 2~3개로 나뉘어 환경변수 연결 실수가 생길 수 있습니다.
- 적합도: 이 프로젝트의 MVP 검증 단계에 가장 적합합니다.

### 2순위: 단일 VPS + Docker + Nginx + PostgreSQL

- 비용: DigitalOcean 같은 VPS는 Basic Droplet이 월 $4~$6대부터 시작합니다. 실사용 운영은 1GB 이상과 백업 비용을 고려하는 편이 현실적입니다.
- 장점: 프론트, 백엔드, DB, Nginx를 한 서버에서 통제할 수 있고 월 고정비 예측이 쉽습니다.
- 단점: HTTPS 인증서, 방화벽, OS 보안 업데이트, PostgreSQL 백업/복구, 장애 대응을 직접 관리해야 합니다.
- 적합도: 서버 운영 경험이 있거나 장기 비용을 낮추고 싶을 때 적합합니다. 초보자 첫 배포로는 1순위보다 부담이 큽니다.

## 운영 배포 순서 예시

1. 운영 PostgreSQL 생성
2. 백엔드 서비스 생성 및 환경변수 등록
3. 백엔드에서 `python -m alembic upgrade head` 실행
4. `python -m app.db.seed_reference_data` 실행
5. `python -m app.db.create_admin --email ...`로 관리자 계정 생성
6. 백엔드 `GET /api/health`, `GET /api/health/db` 확인
7. 프론트 서비스 생성 및 `VITE_API_BASE_URL`, `VITE_FRONTEND_BASE_URL` 등록
8. 프론트 빌드 및 배포
9. 고객 견적 작성, 관리자 로그인, 공유 링크, PDF 다운로드 smoke test

## 검증 명령

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m compileall -q app tests alembic
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m alembic current
```

## 주의

- `backend/.env`, `frontend/.env`, `.venv`, `node_modules`, `frontend/dist`, 캐시 파일은 Git에 포함하지 않습니다.
- `python -m app.db.init_db`는 개발 편의용입니다. 운영 DB 스키마 생성과 변경은 Alembic만 사용합니다.
- `docker-compose.yml`은 로컬 개발용입니다. 운영 DB 비밀번호는 별도 secret 또는 호스팅 환경변수로 관리합니다.
- 운영 DB migration 전에는 백업을 먼저 준비합니다.
- 로그와 오류 응답에 DB 접속정보, 비밀번호, JWT, 공유 token 원문이 노출되지 않도록 유지합니다.
