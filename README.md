<p align="center">
  <img src="frontend/public/burst-logo.svg" alt="Burst Logo" width="120" />
</p>

<h1 align="center">BURST</h1>

<p align="center">
  <strong>AI-powered newsroom that never sleeps.</strong><br/>
  Aggregates raw news, writes editorial-grade articles, produces multimedia, and publishes — fully autonomous, 24/7.
</p>

<p align="center">
  <a href="https://www.burst.fm">burst.fm</a> &nbsp;·&nbsp;
  <a href="#quickstart">Quickstart</a> &nbsp;·&nbsp;
  <a href="#architecture">Architecture</a> &nbsp;·&nbsp;
  <a href="#how-it-works">How It Works</a>
</p>

---

## What is Burst?

Burst is an autonomous news platform built on a **multi-agent system**. It ingests tech news from dozens of sources, routes each story through an AI editorial pipeline — classification, research, writing, editorial review — then produces narrated video segments and distributes them to YouTube, TikTok, and the web.

No human in the loop. No cron-job summaries. A full digital newsroom.

### Key capabilities

- **Multi-source aggregation** — RSS feeds, Twitter/X, Weibo, and web crawlers running on configurable schedules
- **LangGraph editorial workflow** — a stateful graph with flash (quick takes) and deep (investigative) sub-pipelines
- **AI agent team** — Classifier, Researcher, Writer, Chief Editor, and Meta Writer agents with automatic LLM fallback across 9+ providers
- **Multimedia production** — ElevenLabs TTS narration, automated video composition with moviepy, face-aware framing
- **Multi-platform distribution** — YouTube, TikTok, and email delivery
- **Real-time dashboard** — Streamlit-based newsroom monitor with live workflow state via Redis
- **Semantic deduplication** — Vector embeddings (FastEmbed + pgvector) to kill duplicate stories before they enter the pipeline

---

## Architecture

```
                    ┌──────────────────────────────────────────┐
                    │              BURST PLATFORM               │
                    └──────────────────────────────────────────┘

    ┌──────────┐      ┌────────────────┐     ┌────────────┐     ┌──────────────┐
    │ Ingest   │────▶│   Workflow     │────▶│ Production │────▶│ Distribution│
    │ Aggregator│     │ Editorial nodes│     │ Multimedia │     │  (Under Dev) │
    └──────────┘      └────────────────┘     └────────────┘     └──────────────┘
         │                 │                      │                    │
    RSS/Twitter     LangGraph Engine       ElevenLabs TTS       YouTube/TikTok
    Weibo/Web       9+ LLM Providers        Video                    Website
    Tavily API      pgvector Dedup        

    ┌───────────────────────────────────────────────────────────────────────┐
    │                        Infrastructure                                 │
    │   PostgreSQL (pgvector)  ·  Redis  ·  Streamlit Dashboard             │
    └───────────────────────────────────────────────────────────────────────┘
```

#
---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Orchestration** | LangGraph, LangChain |
| **LLM Providers** | Groq, xAI (Grok), Anthropic, Google, OpenAI, DeepSeek, Mistral, Perplexity, Ollama |
| **Database** | PostgreSQL + pgvector, Redis |
| **Search & Scraping** | Tavily, Apify, DuckDuckGo, Trafilatura, Feedparser |
| **TTS & Video** | ElevenLabs, Edge-TTS, moviepy, OpenCV, face-recognition |
| **Frontend** | React, Vite, TailwindCSS, Zustand, React Query |
| **Dashboard** | Streamlit |
| **NLP** | spaCy, FastEmbed (nomic-embed-text-v1.5), scikit-learn |
| **Infra** | Docker Compose, uv, asyncio |

---


---

## Quickstart

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with Pgvector extension
- Redis 7+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Node.js 18+ (for frontend)
- ffmpeg (for video production)

### 1. Infrastructure

```bash
# Spin up Postgres (with pgvector) and Redis
cd scripts && docker compose up -d
```

### 2. Configuration

```bash
# Copy and edit settings
cp config/settings.yaml.template config/settings.yaml

# Set API keys in .env
cp .env.example .env
# Add keys for: GROQ, XAI, ANTHROPIC, OPENAI, GOOGLE, ELEVENLABS, TAVILY, APIFY...
```

### 3. Launch

```bash
# One command — sets up venv, installs deps, inits DB, launches all services
./start.sh launch
```

This starts four async services:

| Service | Entry Point | Port |
|---------|------------|------|
| Aggregator | `main.py` | — |
| Workflow | `main_flow.py` | — |
| Production | `main_production.py` | — |
| Dashboard | `dashboard.py` | 8501 |

```bash
# Check status
./start.sh status

# Graceful shutdown
./start.sh stop
```

### 4. Frontend (optional)

```bash
cd frontend
npm install
npm run dev     # → http://localhost:5173
```

---

## LLM Provider Support

Burst uses a **model factory with automatic fallback** — if a provider is down, requests cascade to the next available LLM. Configure providers via environment variables:

| Provider | Env Variable | Models |
|----------|-------------|--------|
| Groq | `GROQ_API_KEY` | Llama, Mixtral |
| xAI | `XAI_API_KEY` | Grok |
| Anthropic | `ANTHROPIC_API_KEY` | Claude |
| Google | `GOOGLE_API_KEY` | Gemini |
| OpenAI | `OPENAI_API_KEY` | GPT-4o |
| DeepSeek | `DEEPSEEK_API_KEY` | DeepSeek |
| Mistral | `MISTRAL_API_KEY` | Mistral |
| Perplexity | `PERPLEXITY_API_KEY` | Sonar |
| Ollama | — (local) | Any GGUF model |

---

## Development

```bash
# Run tests
pytest tests/ -v
 

# Lint frontend
cd frontend && npm run lint
```

---

## License

This project is MIT. All rights reserved.

---

<p align="center">
  <sub>Built with caffeine, LangGraph, and an unreasonable belief that AI can do journalism.</sub>
</p>
