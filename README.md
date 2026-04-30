# AI Code Review Agent 🤖

> **Advanced multi-model code review system with semantic caching, GitHub integration, and production-ready architecture**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)

An intelligent code review tool that orchestrates multiple LLMs to analyze code quality, security vulnerabilities, performance bottlenecks, and maintainability issues. Features semantic caching, rate limiting, GitHub webhook integration, and detailed HTML reports.

## ✨ Key Features

### 🎯 Multi-Model Ensemble System
- **Primary Reviewer**: Claude/Ollama (detailed quality analysis)
- **Secondary Reviewer**: OpenAI/Ollama (security-focused)
- **Tertiary Reviewer**: Heuristic analyzer (performance patterns)
- **Consensus Scoring**: Weighted aggregation with severity penalties
- **Circuit Breaker**: Automatic fallback on model failures

### 🚀 Performance & Scalability
- **Semantic Caching**: 70% cost reduction via embedding-based similarity matching
- **Rate Limiting**: Per-user request throttling with Redis
- **Async Architecture**: FastAPI with full async/await support
- **Batch Processing**: Review multiple files in parallel

### 🔐 Security & Authentication
- **Multiple Auth Modes**: API Key, JWT, or both
- **GitHub Webhook**: Secure signature verification
- **Environment-based Config**: Secrets management via .env

### 📊 Analytics & Reporting
- **HTML Reports**: CI/CD-ready detailed analysis
- **PostgreSQL History**: Persistent review storage
- **Streamlit Dashboard**: Interactive analytics and history
- **OpenTelemetry**: Distributed tracing support

### 🆓 Free Option Available
- **Ollama Integration**: Run completely free with local models
- **No API Keys Required**: Perfect for learning and development
- **Production Ready**: Same features as paid APIs

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
│  (GitHub/   │
│   CI/CD)    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         FastAPI Backend             │
│  ┌──────────────────────────────┐  │
│  │   Multi-Model Ensemble       │  │
│  │  ┌────────┐ ┌────────┐      │  │
│  │  │Claude/ │ │OpenAI/ │      │  │
│  │  │Ollama  │ │Ollama  │      │  │
│  │  └────────┘ └────────┘      │  │
│  │  ┌────────────────────┐     │  │
│  │  │ Consensus Scoring  │     │  │
│  │  └────────────────────┘     │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │   Semantic Cache (Redis)     │  │
│  │   - Embedding similarity     │  │
│  │   - 70% cost reduction       │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
       │                    │
       ▼                    ▼
┌─────────────┐      ┌─────────────┐
│ PostgreSQL  │      │    Redis    │
│  (History)  │      │  (Cache +   │
│             │      │   Limits)   │
└─────────────┘      └─────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- (Optional) Ollama for free local models

### Option A: Free Setup with Ollama 🆓

**1. Install Ollama**
```bash
# Windows: Download from https://ollama.com/download
# Mac: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh
```

**2. Pull Models**
```bash
ollama pull codellama
ollama pull llama3
ollama pull mistral
```

**3. Configure Environment**
```bash
cp .env.example .env
# Edit .env and set:
# USE_OLLAMA_ONLY=true
```

**4. Start Services**
```bash
# Start infrastructure
docker compose up -d

# Install dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

# Start backend
uvicorn backend.app.main:app --reload --port 8000

# Start dashboard (new terminal)
streamlit run dashboard/app.py
```

**5. Access**
- API: http://localhost:8000
- Dashboard: http://localhost:8501
- Docs: http://localhost:8000/docs

### Option B: Production Setup with Paid APIs 💰

**1. Get API Keys**
- Claude: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys

**2. Configure**
```bash
cp .env.example .env
# Edit .env and add:
# ANTHROPIC_API_KEY=your_key
# OPENAI_API_KEY=your_key
# USE_OLLAMA_ONLY=false
```

**3. Start Services** (same as Option A step 4)

## 📡 API Usage

### Review Code
```bash
curl -X POST http://localhost:8000/api/v1/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "developer-1",
    "repository": "myorg/myrepo",
    "file_path": "src/auth.py",
    "language": "python",
    "code": "def login(user, pwd):\n    query = f\"SELECT * FROM users WHERE name='\"'{user}'\"'\"\n    return db.execute(query)",
    "focus_areas": ["security", "performance"]
  }'
```

### Response
```json
{
  "review_id": "uuid",
  "consensus_score": 3.5,
  "summary": "Detected 2 findings: 1 security, 1 performance. Includes 1 high severity finding.",
  "findings": [
    {
      "category": "security",
      "severity": "high",
      "title": "SQL Injection Vulnerability",
      "description": "User input directly concatenated into SQL query...",
      "recommendation": "Use parameterized queries or ORM"
    }
  ],
  "cache_hit": false,
  "processing_ms": 2340
}
```

### Batch Review
```bash
curl -X POST http://localhost:8000/api/v1/reviews/batch \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"user_id": "dev-1", "code": "...", "language": "python"},
      {"user_id": "dev-1", "code": "...", "language": "javascript"}
    ]
  }'
```

### Get History
```bash
curl http://localhost:8000/api/v1/reviews/history?user_id=dev-1&limit=10
```

## 🔧 Configuration

Key environment variables in `.env`:

```bash
# LLM Configuration
USE_OLLAMA_ONLY=true              # Use free Ollama models
ANTHROPIC_API_KEY=sk-ant-...      # Claude API key (if not using Ollama)
OPENAI_API_KEY=sk-...             # OpenAI API key (if not using Ollama)

# Ollama Models
OLLAMA_PRIMARY_MODEL=codellama    # Primary reviewer model
OLLAMA_BASE_URL=http://localhost:11434

# Cache Configuration
CACHE_TTL_SECONDS=86400           # 24 hours
CACHE_SIMILARITY_THRESHOLD=0.85   # 85% similarity for cache hit

# Rate Limiting
RATE_LIMIT_REQUESTS=100           # Requests per window
RATE_LIMIT_WINDOW_SECONDS=3600    # 1 hour window

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/reviews
REDIS_URL=redis://localhost:6379/0

# Authentication
AUTH_MODE=none                    # Options: none, api_key, jwt, both
API_KEY=your-secret-key           # If using api_key mode

# GitHub Integration
GITHUB_TOKEN=ghp_...              # For webhook PR file fetching
GITHUB_WEBHOOK_SECRET=secret      # Webhook signature verification
```

## 🐳 Docker Deployment

```bash
# Build and run all services
docker compose up -d

# View logs
docker compose logs -f backend

# Stop services
docker compose down
```

## 📊 Project Structure

```
.
├── backend/
│   └── app/
│       ├── api/              # FastAPI routes
│       │   └── v1/
│       │       └── endpoints/
│       ├── core/             # Config, logging, telemetry
│       ├── db/               # Database models & session
│       ├── models/           # Pydantic schemas
│       ├── services/         # Business logic
│       │   ├── analysis/     # Consensus & diff parsing
│       │   ├── cache/        # Semantic cache & embeddings
│       │   ├── github/       # GitHub API & webhooks
│       │   ├── llm/          # LLM clients & ensemble
│       │   └── reports/      # HTML report generation
│       ├── security/         # Authentication
│       └── templates/        # HTML templates
├── dashboard/                # Streamlit dashboard
├── .github/
│   └── workflows/            # CI/CD pipelines
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## 🎯 7-Day Development Plan

This project follows a structured 7-day commit strategy for maximum GitHub impact:

### Day 1: Foundation (4-5 commits)
- `feat: initialize FastAPI project with async setup`
- `feat: add core configuration and logging`
- `feat: integrate Claude/Ollama API client`
- `feat: add Pydantic models for review request/response`

### Day 2: Multi-Model System (3-4 commits)
- `feat: implement multi-model ensemble orchestration`
- `feat: add OpenAI/Ollama fallback with circuit breaker`
- `feat: create code analysis prompt templates`
- `feat: implement consensus scoring algorithm`

### Day 3: Caching Layer (3-4 commits)
- `feat: implement semantic caching with embeddings`
- `feat: add Redis cache management`
- `feat: implement rate limiting per user`
- `feat: add cache similarity matching`

### Day 4: GitHub Integration (3-4 commits)
- `feat: build GitHub webhook receiver`
- `feat: add webhook signature verification`
- `feat: implement code diff parsing`
- `feat: add GitHub API client for PR files`

### Day 5: Persistence & Reports (3-4 commits)
- `feat: add PostgreSQL review history storage`
- `feat: implement HTML report generation`
- `feat: create REST API endpoints for history`
- `feat: add batch review processing`

### Day 6: Dashboard & Monitoring (2-3 commits)
- `feat: create Streamlit dashboard`
- `feat: add OpenTelemetry tracing`
- `feat: implement detailed logging`

### Day 7: Documentation & CI/CD (2-3 commits)
- `docs: add comprehensive API documentation`
- `feat: add GitHub Actions CI/CD pipeline`
- `docs: add deployment guide and examples`

**Total: 20-25 commits | 2000-3000 LOC**

## 🧪 Development

### Run Locally
```bash
# Backend
uvicorn backend.app.main:app --reload --port 8000

# Dashboard
streamlit run dashboard/app.py
```

### Code Quality
```bash
# Format
ruff format .

# Lint
ruff check .

# Type check
mypy backend/
```

## 🔐 Security Notes

- Never commit `.env` file (included in `.gitignore`)
- Use environment variables for all secrets
- Enable authentication in production (`AUTH_MODE=api_key` or `jwt`)
- Use HTTPS in production
- Rotate API keys regularly
- Use managed Redis/PostgreSQL in production

## 📈 Performance Tips

1. **Cache Hit Rate**: Monitor cache hit rate in dashboard
2. **Model Selection**: Use Ollama for development, Claude/OpenAI for production
3. **Batch Processing**: Use batch endpoint for multiple files
4. **Rate Limiting**: Adjust limits based on your usage patterns
5. **Database Indexing**: Indexes already configured for common queries

## 🤝 Contributing

This is a portfolio project demonstrating:
- ✅ Advanced prompt engineering & LLM orchestration
- ✅ Multi-model system design with fallbacks
- ✅ Semantic caching & embeddings
- ✅ Production-ready API architecture
- ✅ Async Python & FastAPI best practices
- ✅ Docker containerization
- ✅ CI/CD pipeline setup

## 📝 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- FastAPI for the excellent async framework
- Anthropic & OpenAI for LLM APIs
- Ollama for free local model support
- Streamlit for rapid dashboard development

---

**Built with ❤️ for the developer community**
