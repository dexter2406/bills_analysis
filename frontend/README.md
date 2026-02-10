# Frontend M1 (React + Vite + Tailwind)

M1 frontend for bills upload workflow. This app follows frozen `v1` backend contracts under `src/bills_analysis/models/`.

## Stack
- React 18 + Vite
- Tailwind CSS
- JavaScript + JSDoc + Zod runtime schemas
- Vitest + Testing Library

## Quick start
1. Enable pnpm via corepack (preferred):
   - `corepack enable`
   - `corepack prepare pnpm@latest --activate`
2. Install dependencies:
   - `pnpm install`
3. Run dev server:
   - `pnpm dev`
4. Run tests:
   - `pnpm test`

## Environment
Copy `.env.example` as `.env.local` and adjust when needed:

- `VITE_API_MODE=mock|real`
- `VITE_API_BASE_URL=http://127.0.0.1:8000`

Default mode is `mock`.

## API Mode Strategy
- `mock`: full frontend flow without backend upload endpoint.
- `real`: uses current `/v1/batches*` backend endpoints.
- Real multipart upload is intentionally deferred. Upload details must stay inside `uploadClient.real` only.

## Folder highlights
- `src/contracts/`: strict v1 runtime schemas and JSDoc typedefs
- `src/features/upload/api/`: mock/real upload clients and mode switch
- `src/features/upload/state/`: reducer + flow hook with polling/retry
- `src/features/upload/pages/BillUploadPage.jsx`: M1 upload page

## Contract alignment
Current client contracts map to:
- `POST /v1/batches`
- `GET /v1/batches`
- `GET /v1/batches/{batch_id}`
- `PUT /v1/batches/{batch_id}/review`
- `POST /v1/batches/{batch_id}/merge`

Validation notes:
- `run_date` follows `DD/MM/YYYY`
- unknown fields are rejected in runtime schema parsing
- enums match backend values 1:1
