# ⚡ ResolvIQ — AI-Powered Enterprise Incident Management

> Intelligent incident & ticket management platform with LLM-powered root cause analysis, SOP generation, log analysis, and real-time SLA monitoring. Built with FastAPI + React, powered by AWS Bedrock (Claude 3.5 Sonnet).

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![AWS Bedrock](https://img.shields.io/badge/AWS_Bedrock-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Claude](https://img.shields.io/badge/Claude_3.5-D97757?style=for-the-badge&logo=anthropic&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

---

## 🤖 AI Engineering Highlights

This project demonstrates hands-on, production-grade AI engineering across the full stack:

| Competency | How It's Demonstrated in This Project |
|-----------|----------------------------------------|
| **Python & Software Engineering** | Async FastAPI backend built with clean architecture — repository pattern, service layer, dependency injection, Pydantic v2 validation, and SQLAlchemy 2.0 ORM. |
| **AI Applications with FastAPI** | RESTful microservice endpoints for AI features (log analysis, RCA, SOP, chat) with streaming-ready async handlers, retry logic, and graceful error handling. |
| **LLMs & Generative AI** | Integrated **Claude 3.5 Sonnet via AWS Bedrock** for multi-modal reasoning — text + vision (analyzing uploaded screenshots, PDFs, and logs). Pluggable provider design supporting both cloud (Bedrock) and local (Ollama) inference. |
| **Prompt Engineering** | Structured system prompts with role-specific instructions, JSON-schema-enforced outputs, and response normalization to handle model output variability. Few-shot style guidance for RCA (5-Whys), SOP generation, and log triage. |
| **Multi-Modal AI** | Vision-enabled analysis — feeds base64-encoded images and extracted document text (PDF/DOCX) into the LLM context for richer incident understanding. |
| **AI Guardrails & Governance** | Role-based access control on AI features, input size limits, content truncation, output validation, and provider-level fallback to prevent failures. |
| **AWS Services** | **Bedrock** (LLM inference), **EC2** (compute), **RDS PostgreSQL** (managed DB), **S3** (file storage & attachments), **SES** (email), **IAM** (access control), **CloudWatch**-ready logging. |
| **Enterprise Integration** | AI layer integrated with PostgreSQL data, S3 document store, incident history, and comment threads — persisting all AI interactions per ticket for auditability. |
| **Containerization & CI/CD** | Fully Dockerized (multi-stage builds), orchestrated with Docker Compose, GitHub Actions CI/CD pipeline, deployed to AWS. |
| **System Design & Scalability** | Redis caching (30s TTL with invalidation), RabbitMQ + Celery for async task processing, token-bucket rate limiting, connection pooling, and horizontal-scaling-ready worker architecture. Load-tested with Locust. |

**Roadmap (in progress):** RAG-based knowledge retrieval over historical incidents using vector embeddings; agentic multi-step incident resolution with LangGraph orchestration.

---

## 📋 Table of Contents

- [Overview](#overview)
- [AI Capabilities](#ai-capabilities)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Project Structure](#project-structure)

---

## AI Capabilities

The AI engine (AWS Bedrock / Claude 3.5 Sonnet, with local Ollama fallback) powers:

| Feature | Description |
|---------|-------------|
| **Log Analysis** | Paste raw logs → AI identifies root cause, severity, affected components, and step-by-step fixes with actual commands. |
| **Root Cause Analysis (RCA)** | Generates structured 5-Whys RCA reports with contributing factors, timeline, corrective & preventive actions. |
| **SOP Generation** | Produces detailed Standard Operating Procedures with prerequisites, step-by-step commands, escalation criteria, and rollback procedures. |
| **Resolution Suggestions** | AI-recommended fixes with specific commands, config changes, and effort estimates. |
| **Contextual Chat** | Multi-turn chat with full ticket context — reads description, comments, attachments (text, PDF, DOCX), and images (vision). Conversations persisted per ticket. |
| **Multi-Modal Understanding** | Analyzes uploaded screenshots (vision), extracts text from PDF/DOCX, and reads log files for complete incident context. |

---

## Overview

A full-stack enterprise incident management system designed for IT operations teams. It provides end-to-end incident lifecycle management — from creation and assignment to AI-powered root cause analysis and resolution.

**Key Highlights:**
- 🤖 **AI-Powered Analysis** — Generate RCA, SOP, and resolution suggestions using local Ollama or AWS Bedrock
- ⏱️ **Real-time SLA Monitoring** — Live countdown timers with automatic escalation
- 👥 **Role-Based Access Control** — 5 distinct roles with granular permissions
- 📊 **Analytics Dashboard** — 8+ metrics, trends, team/engineer performance
- 🔔 **Real-time Notifications** — WebSocket + Email (Celery + SMTP/SES)
- 🌙 **Modern UI** — Dark mode, responsive design, accessible

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│                  React + Vite + Tailwind CSS v4                      │
│         (Dashboard, Incidents, AI Assistant, Admin Panel)            │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ REST API + WebSocket
┌────────────────────────────────┼────────────────────────────────────┐
│                           BACKEND                                    │
│                     FastAPI (Async Python)                           │
│                                │                                     │
│  ┌──────────┐  ┌──────────┐  ┌┴─────────┐  ┌──────────┐           │
│  │   Auth   │  │Incidents │  │Analytics │  │    AI    │           │
│  │  (JWT)   │  │  (CRUD)  │  │(Metrics) │  │(Ollama/ │           │
│  │  RBAC    │  │  SLA     │  │Dashboard │  │ Bedrock)│           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌────────┴───────┐    ┌─────────┴────────┐    ┌────────┴───────┐
│   PostgreSQL   │    │      Redis       │    │   RabbitMQ     │
│  (Primary DB)  │    │ (Cache + Rate    │    │ (Message Queue)│
│                │    │   Limiting)      │    │                │
└────────────────┘    └──────────────────┘    └───────┬────────┘
                                                      │
                                              ┌───────┴────────┐
                                              │  Celery Worker  │
                                              │ (Email, SLA    │
                                              │  Checks, Tasks)│
                                              └────────────────┘
```

---

## Features

### 🎫 Incident Management
- Create, update, delete incidents with full audit trail
- Priority levels: Low, Medium, High, Critical
- Status workflow: Open → In Progress → Resolved → Closed
- Comments and change history tracking
- File attachments (S3)
- CSV export for reporting

### 🤖 AI Assistant (Ollama / AWS Bedrock)
- **Log Analysis** — Upload logs, get root cause and fix suggestions
- **Suggest Fixes** — AI-powered resolution recommendations
- **Generate SOP** — Standard Operating Procedures from incidents
- **Generate RCA** — 5-Whys Root Cause Analysis reports
- **Contextual Chat** — Chat with AI about specific incidents
- **Conversation Persistence** — Chat history saved per incident

### ⏱️ SLA Management
- Auto-calculated SLA deadlines based on priority
- Real-time countdown timers (D:H:M format)
- Color-coded status (Healthy → Warning → Critical → Breached)
- Automatic escalation on SLA breach
- SLA compliance metrics on dashboard

### 📊 Analytics Dashboard
- Open Incidents, Resolved Today, Critical, SLA Breached
- Monthly creation/resolution trends
- Top Engineers by resolution rate
- Top Teams performance
- Priority breakdown
- Average resolution time

### 👥 Role-Based Access Control
| Role | Permissions |
|------|-------------|
| **Admin** | Full access, user management, delete anything |
| **Incident Manager** | Assign, escalate, view audit logs, analytics |
| **Team Lead** | Assign, escalate, manage team incidents |
| **Engineer** | Create, update, resolve assigned incidents |
| **Customer** | Create incidents, view only their own tickets |

### 🔔 Notifications
- Real-time WebSocket notifications
- Email notifications (Celery + SMTP/SES)
- In-app notification bell with unread count
- Triggered on: assignment, escalation, SLA breach

### 🛠️ Admin Panel
- User management (create, deactivate, activate)
- Department & Team management
- Assign users to departments
- Audit logs viewer
- SLA compliance metrics

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite, Tailwind CSS v4, React Query, React Router |
| **Backend** | FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic |
| **Database** | PostgreSQL 16 |
| **Cache** | Redis 7 |
| **Queue** | RabbitMQ 3.13, Celery 5 |
| **AI** | Ollama (local) / AWS Bedrock (production) |
| **Auth** | JWT (access + refresh tokens), bcrypt |
| **Email** | SMTP / AWS SES |
| **Storage** | AWS S3 |
| **Container** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |
| **Proxy** | Nginx |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose
- Ollama (for AI features)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/enterprise-incident-management.git
cd enterprise-incident-management

# 2. Start infrastructure (PostgreSQL, Redis, RabbitMQ)
docker-compose up postgres redis rabbitmq -d

# 3. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env     # Configure your environment variables
alembic upgrade head     # Run database migrations
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Frontend setup (new terminal)
cd frontend
npm install
npm run dev

# 5. Celery worker (new terminal, for email/background tasks)
cd backend
celery -A app.workers.celery_app worker --loglevel=info --pool=solo

# 6. Ollama (for AI features)
ollama pull llama3.2:1b  # or qwen2.5:7b for better quality
```

### Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API Docs | http://localhost:8000/api/docs |
| RabbitMQ Dashboard | http://localhost:15672 (guest/guest) |

---

## Environment Variables

Create `backend/.env`:

```env
# App
DEBUG=True
API_V1_PREFIX=/api/v1

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/incident_management
DATABASE_URL_SYNC=postgresql://postgres:password@localhost:5432/incident_management

# Redis
REDIS_URL=redis://localhost:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672//

# JWT
JWT_SECRET_KEY=your-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI (Local - Ollama)
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b

# AI (Production - AWS Bedrock)
# AI_PROVIDER=bedrock
# BEDROCK_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0

# AWS
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=incident-management-uploads

# Email
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=noreply@yourdomain.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587

# Frontend
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173
```

---

## API Documentation

Interactive API docs available at `http://localhost:8000/api/docs` (Swagger UI).

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login & get tokens |
| POST | `/api/v1/auth/register` | Register new user |
| GET | `/api/v1/incidents/` | List incidents (filtered) |
| POST | `/api/v1/incidents/` | Create incident |
| PATCH | `/api/v1/incidents/{id}` | Update incident |
| GET | `/api/v1/analytics/dashboard` | Dashboard metrics |
| POST | `/api/v1/ai/analyze-logs` | AI log analysis |
| POST | `/api/v1/ai/generate-rca` | Generate RCA report |
| POST | `/api/v1/ai/generate-sop` | Generate SOP |
| POST | `/api/v1/ai/chat` | Chat with AI |
| GET | `/api/v1/ai/history/{id}` | Get AI interaction history |

---

## Deployment

### Production Architecture (AWS)

```
Route 53 → CloudFront → S3 (Frontend)
                ↓
         ALB → ECS/EC2 (Backend API)
                ├── RDS PostgreSQL
                ├── ElastiCache Redis
                ├── AWS Bedrock (AI)
                ├── S3 (File Storage)
                ├── SES (Email)
                └── CloudWatch (Monitoring)
```

### Docker Production Build

```bash
# Build and run all services
docker-compose -f docker-compose.yml up --build

# Or build individually
docker build -t incident-backend ./backend
docker build -f frontend/Dockerfile.prod -t incident-frontend ./frontend
```

### AWS Services Used

| Service | Purpose |
|---------|---------|
| EC2 / ECS Fargate | Backend hosting |
| RDS PostgreSQL | Managed database |
| ElastiCache Redis | Caching & rate limiting |
| S3 | File uploads + Frontend hosting |
| AWS Bedrock | AI (Claude 3.5 Sonnet) |
| CloudFront | CDN for frontend |
| SES | Email notifications |
| CloudWatch | Monitoring & logs |
| Route 53 | DNS management |

---

## Project Structure

```
enterprise-incident-management/
├── backend/
│   ├── app/
│   │   ├── auth/           # Authentication & user management
│   │   ├── incidents/      # Incident CRUD & lifecycle
│   │   ├── notifications/  # WebSocket & email notifications
│   │   ├── analytics/      # Dashboard & metrics
│   │   ├── ai/             # AI service (Ollama/Bedrock)
│   │   ├── teams/          # Teams & departments
│   │   ├── files/          # S3 file storage
│   │   ├── audit/          # Audit logging
│   │   ├── search/         # Full-text search
│   │   ├── workers/        # Celery background tasks
│   │   ├── core/           # Config, security, dependencies
│   │   ├── db/             # Database connection & base
│   │   ├── models/         # SQLAlchemy models
│   │   ├── middleware/     # Rate limiting, logging, CORS
│   │   └── main.py         # FastAPI application entry
│   ├── migrations/         # Alembic database migrations
│   ├── tests/              # Pytest test suite
│   ├── Dockerfile          # Production Docker image
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/          # Route pages (Dashboard, Incidents, AI, Admin)
│   │   ├── components/     # Reusable UI components
│   │   ├── context/        # React context (Auth, Theme)
│   │   ├── hooks/          # Custom hooks (WebSocket)
│   │   ├── services/       # API service layer
│   │   ├── layouts/        # Page layouts (MainLayout)
│   │   └── utils/          # Timezone, helpers
│   ├── Dockerfile          # Dev Docker image
│   ├── Dockerfile.prod     # Production multi-stage build
│   └── package.json        # Node.js dependencies
├── nginx/                  # Reverse proxy configuration
├── .github/workflows/      # CI/CD pipelines
├── docker-compose.yml      # Full-stack Docker orchestration
└── README.md
```

---

## 📄 License

This project is for educational and portfolio purposes.

---

## 🙋 Author

**Jay Valaki**

Built with ❤️ using modern full-stack technologies.
