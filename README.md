# Startup Ideas Collector 🚀

Automated system that finds real startup ideas by analyzing problems people discuss on Reddit and Hacker News using AI agents.

## 🎯 What It Does

- **Scrapes** Reddit and Hacker News for real problems people complain about
- **Analyzes** discussions using Claude AI to extract startup opportunities
- **Validates** ideas with market research, competitive analysis, and trend data
- **Presents** startup briefs with confidence scores through a web interface

## 🏗️ Architecture

**Weekend MVP (Phase 0):**
- 2 AI agents: Problem Analyzer + Marketing Agent
- 2 data sources: Reddit + Hacker News
- SQLite database
- FastAPI backend + Next.js frontend
- Cost: ~$2-5/day with smart filtering

**Future Phases:**
- Week 2: Validator Agent
- Week 3: Design + Tech Architect Agents
- Week 4: Trend Analyst Agent (Google Trends)

## 📦 Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Step 1: Clone & Setup

```bash
cd ~/projects/startup-ideas
cp .env.example .env
```

### Step 2: Get API Credentials

**Anthropic Claude API** (required):
1. Go to https://console.anthropic.com/
2. Create API key
3. Add to `.env`: `ANTHROPIC_API_KEY=your_key`

**Tavily API** (required for market research):
1. Sign up at https://tavily.com
2. Get free tier API key (1000 requests/month)
3. Add to `.env`: `TAVILY_API_KEY=your_key`

**Reddit API** (required):
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" → Choose "script"
3. Copy client_id and client_secret
4. Add to `.env`:
   ```
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_secret
   ```

### Step 3: Install Backend Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### Step 4: Initialize Database

```bash
python -c "from db.database import init_db; init_db()"
```

### Step 5: Install Frontend Dependencies (Day 2)

```bash
cd ../frontend
npm install
```

## 🚀 Usage

### Test API Keys Configuration

Before starting, verify all API keys are working:

```bash
./test-api-keys.sh
```

### Start Backend (Port 8000)

```bash
./start-backend.sh
```

Or manually:
```bash
cd backend
source venv/bin/activate
PYTHONPATH=. uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**API Documentation**: http://localhost:8000/docs

### Start Frontend (Port 3000) - Coming in Day 2

```bash
cd frontend
npm run dev
```

### Manual Scraping & Analysis

Via API (recommended):
```bash
# Scrape Reddit
curl -X POST "http://localhost:8000/api/scrape?source=reddit&limit=5&analyze=true"

# Scrape Hacker News
curl -X POST "http://localhost:8000/api/scrape?source=hackernews&limit=5&analyze=true"

# Scrape both
curl -X POST "http://localhost:8000/api/scrape?source=all&limit=10&analyze=true"
```

Or via Python:
```bash
# Test scrapers
cd backend && source venv/bin/activate
PYTHONPATH=. python agents/scrapers/reddit_agent.py
PYTHONPATH=. python agents/scrapers/hackernews_agent.py

# Test analyzers
PYTHONPATH=. python agents/analyzers/problem_analyzer.py
PYTHONPATH=. python agents/analyzers/marketing_agent.py

# Test full pipeline
PYTHONPATH=. python services/orchestrator.py
```

## 📊 Configuration

Edit `backend/config.yaml` to customize:
- Subreddits to monitor
- Keywords to search for
- Minimum upvote thresholds
- Batch sizes

## 🧪 Testing

```bash
# Test Reddit scraper
python -m agents.scrapers.reddit_agent

# Test Problem Analyzer
python -m agents.analyzers.problem_analyzer

# Test full pipeline
python -m services.orchestrator
```

## 📝 Development Roadmap

**Day 1 - Backend MVP (COMPLETED)** ✅
- [x] Project setup
- [x] Database models with 9 tables
- [x] Reddit scraper with PRAW
- [x] Hacker News scraper with API
- [x] Problem Analyzer agent (Haiku filter + Sonnet analysis)
- [x] Marketing Agent with Tavily API integration
- [x] Orchestrator with score calculation
- [x] FastAPI backend with 8 endpoints
- [x] Startup scripts and configuration

**Day 2 - Frontend (TODO)**
- [ ] Next.js frontend setup
- [ ] Dashboard with stats
- [ ] Problems list page
- [ ] Problem detail page with tabs
- [ ] API integration

**Week 2+**
- [ ] Validator Agent (existing solutions search)
- [ ] Design + Tech Agents (Week 3)
- [ ] Trend Analyst with Google Trends (Week 4)
- [ ] Scheduling & automation

## 💰 Cost Optimization

**3-Tier Analysis System:**
- **Tier 1**: Haiku filter ($0.001/discussion) - filters 70-80% noise
- **Tier 2**: Problem + Marketing analysis ($0.05/problem) - basic validation
- **Tier 3**: Full 6-agent analysis ($0.20/problem) - deep dive for high-confidence ideas

**Expected daily cost:** $2-5/day (vs $30/day without filtering)

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **AI**: Anthropic Claude (Haiku + Sonnet)
- **Web Search**: Tavily API
- **Scraping**: PRAW (Reddit), HN API
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Deployment**: Local (localhost)

## 📖 Documentation

- [Implementation Plan](/.claude/plans/optimized-rolling-moth.md)
- [API Documentation](http://localhost:8000/docs) - auto-generated by FastAPI

## 🤝 Contributing

This is a personal project. Feel free to fork and adapt!

## 📄 License

MIT
