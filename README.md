# Orca Monorepo

Orca is an AI agent with a Next.js frontend and Python services. This repo is managed with pnpm workspaces.

## Structure
- `apps/web` — Next.js 14 app (TypeScript, App Router)
- `services/` — Backend services (to be added)
- `packages/` — Shared libraries (optional)
- `infra/` — Infra and CI/CD (to be added)

## Requirements
- Node 18+ (recommend 20+)
- pnpm 9+

## Quick Start
```bash
# From repo root
pnpm install
pnpm web:dev
# Open http://localhost:3000
```

## Scripts (from repo root)
- `pnpm web:dev` — Next.js dev server
- `pnpm web:build` — Build Next.js app
- `pnpm web:start` — Start Next.js production server
- `pnpm web:lint` — Lint web app

## Contributing
- Use feature branches and PRs.
- Keep changes small and focused.
- Add tests where applicable.

## License
TBD
