# ResolvIQ — Project Technical Summary

## What It Is
An AI-powered enterprise incident/ticket management system where users create tickets, and AI (Claude 3.5 via AWS Bedrock) analyzes logs, generates RCA/SOP reports, and provides contextual chat — with real-time SLA tracking and role-based workflows.

---

## Architecture

**Full-stack, containerized, deployed on AWS:**
```
React (Vite + Tailwind) → FastAPI (async) → PostgreSQL (RDS)
                                ├── Redis (caching, rate limiting)
                                ├── RabbitMQ + Celery (async tasks)
                                ├── AWS Bedrock / Ollama (AI)
                                └── S3 (file storage)
```

---

## Backend (FastAPI + Python)

- **Clean architecture:** Repository pattern → Service layer → Routes, with dependency injection
- **Async throughout:** SQLAlchemy 2.0 async ORM, asyncpg driver
- **Auth:** JWT (access + refresh tokens), bcrypt password hashing, token rotation, refresh interceptor
- **RBAC:** 5 roles (Admin, Incident Manager, Team Lead, Engineer, Customer) with `require_role` dependency
- **Validation:** Pydantic v2 schemas
- **Migrations:** Alembic
- **Middleware:** Token-bucket rate limiter (per-IP), request logging, CORS
- **Custom exception handlers** for consistent JSON errors

## Frontend (React 19 + Vite + Tailwind v4)

- **State/data:** React Query (caching, invalidation, optimistic updates via `setQueryData`)
- **Routing:** React Router with protected routes
- **Auth context** with auto token refresh
- **Features:** Dark mode, responsive (mobile hamburger), error boundary, loading skeletons, debounced search
- **Timezone-aware** date rendering (per-user timezone)

---

## Core Features

| Module | Details |
|--------|---------|
| **Tickets** | CRUD, sequential ticket numbers (PostgreSQL sequence), priority/severity, 6 statuses (open, in_progress, pending, hold, closed, escalated), comments with user attribution, change history |
| **SLA** | Auto-calculated deadlines by priority, real-time countdown timer (D:H:M), color-coded urgency, auto-escalation via Celery beat |
| **Assignment** | Searchable dropdown, any staff can assign, tracked in history |
| **Dashboard** | Clickable KPI cards (filter tickets), priority distribution, recent tickets, top teams/engineers, Redis-cached |
| **Admin** | User management (add/deactivate/activate), department assignment, teams/departments CRUD, audit logs |
| **Notifications** | WebSocket real-time + email (Celery + SMTP/SES), notification bell |
| **Profile** | Editable name, timezone selection |

---

## AI Engine (the differentiator)

- **Provider:** AWS Bedrock (Claude 3.5 Sonnet) with pluggable local Ollama fallback — switched via `AI_PROVIDER` env var
- **Features:** Log analysis, RCA (5-Whys), SOP generation, resolution suggestions, contextual chat
- **Multi-modal:** Reads text files, extracts PDF/DOCX content (PyPDF2, python-docx), analyzes images via Claude vision (base64)
- **Context-aware:** Feeds ticket description + comments + history + attachments into prompts
- **Prompt engineering:** Structured system prompts, JSON-schema-enforced output, key normalization to handle model variability
- **Persistence:** All AI interactions saved per ticket (`ai_interactions` table) — chat history restored on revisit
- **Guardrails:** RBAC on AI endpoints, input size limits, output validation, graceful fallback

---

## Infrastructure & DevOps

- **Docker:** Multi-stage builds, Docker Compose orchestration (backend, frontend/nginx, redis, rabbitmq, celery)
- **AWS:** EC2 (compute), RDS PostgreSQL (managed DB), S3 (files), SES (email), Bedrock (AI), IAM
- **CI/CD:** GitHub Actions
- **Nginx:** Reverse proxy (API + WebSocket + static frontend)
- **Load tested:** Locust (identified bcrypt & analytics bottlenecks, solved with Redis caching — dashboard 4s → <10ms)

---

## Key Engineering Decisions

1. **Redis caching** with 30s TTL + invalidation on writes → 130x faster dashboard
2. **Celery + RabbitMQ** for async emails/SLA checks → non-blocking API
3. **Pluggable AI provider** → free local dev (Ollama), powerful prod (Bedrock)
4. **Soft-delete users** (deactivate) → preserves FK integrity for audit trail
5. **Optimistic cache updates** → instant UI feedback on ticket changes
6. **Per-user dashboard caching** → maintains customer data isolation

---

## Skills Demonstrated

- **AI/ML:** LLM integration, prompt engineering, multi-modal AI, AI guardrails, Bedrock/Claude
- **Backend:** Python, FastAPI, async, SQLAlchemy, PostgreSQL, JWT auth, RBAC, REST design
- **Frontend:** React, state management, responsive UI, UX patterns
- **Infra:** Docker, AWS (EC2/RDS/S3/Bedrock/SES/IAM), CI/CD, Nginx
- **System Design:** Caching, message queues, rate limiting, horizontal scaling, load testing

---

## Data Model (core tables)
`users` · `incidents` (tickets) · `incident_comments` · `incident_history` · `attachments` · `ai_interactions` · `notifications` · `audit_logs` · `departments` · `teams` · `refresh_tokens`

---

## Roadmap
- RAG-based knowledge retrieval over historical incidents using vector embeddings
- Agentic multi-step incident resolution with LangGraph orchestration
