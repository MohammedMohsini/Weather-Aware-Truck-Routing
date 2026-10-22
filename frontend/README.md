# Frontend

The frontend is a React, TypeScript, and Vite application. It calls the Django API using `VITE_API_BASE_URL`.

## Local development

```powershell
Copy-Item .env.example .env.local
npm ci
npm run dev
```

For production, set `VITE_API_BASE_URL` in the Vercel project environment to the backend base URL (without `/api`) and rebuild.

## Build

```powershell
npm run build
```

## Quality checks

```powershell
npm run lint
npm run format
```
