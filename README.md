# 🤖 AI News Digest

An AI-powered multi-type newsletter system that ingests RSS feeds, generates intelligent summaries, and delivers professional newsletters via email. Supports multiple newsletter types (Business, Tech, Market, News, Industry) with modular prompt templates and easy Docker deployment.

## ✨ Features

- **5 Newsletter Types**: General Business, Tech Focus, Market Pulse, General News, Industry Specific
- **Modular Prompt System**: Newsletter-specific templates with custom prompts
- **Multi-AI Provider Support**: OpenAI, Gemini, Anthropic with automatic fallback
- **Flexible Email Delivery**: Resend API or SMTP (Gmail, Outlook, corporate)
- **Professional Formatting**: Clean markdown with market tables and visual indicators
- **Web Dashboard**: Modern React interface for management
- **Docker Ready**: One-command deployment with docker-compose

## 🚀 Quick Start

### 1. Clone and Configure
```bash
git clone https://github.com/jsnider89/ai-news-digest.git
cd ai-news-digest
cp .env.example .env
```

### 2. Edit Configuration
Edit `.env` with your API keys:
```bash
# Required: At least one AI provider
OPENAI_API_KEY="sk-your-openai-key"

# Required: Email delivery (choose one)
RESEND_API_KEY="re_your-resend-key"
# OR configure SMTP (see .env.example)

# Optional: Customize settings
PORT=8000
DEFAULT_TIMEZONE="America/New_York"
```

### 3. Deploy with Docker
```bash
docker-compose up -d
```

### 4. Access Dashboard
Visit `http://localhost:8000` to:
- Create newsletters
- Configure RSS feeds
- Set up schedules
- Monitor runs

## 📧 Email Configuration

### Option 1: Resend (Recommended)
```env
RESEND_API_KEY="re_your-key-here"
RESEND_FROM_EMAIL="newsletters@yourdomain.com"
```

### Option 2: SMTP (Gmail, Outlook, etc.)
```env
EMAIL_BACKEND="smtp"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
SMTP_USE_TLS=true
```

## 📊 Newsletter Types

1. **General Business** - Corporate strategy, economics, business intelligence
2. **Tech Focus** - Technology innovation, startups, digital transformation
3. **Market Pulse** - Financial markets, trading, investment analysis
4. **General News** - Comprehensive current events coverage
5. **Industry Specific** - Deep sector expertise (customizable)

## 🐳 Alternative Deployment

### Local Development
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
.venv/bin/python -m app.tasks.prestart
.venv/bin/uvicorn app.web.main:app --reload
```

### Docker Build
```bash
docker build -t ai-news-digest .
docker run --env-file .env -p 8000:8000 ai-news-digest
```

## 🔧 Configuration Options

See `.env.example` for all available options including:
- Custom ports and hosts
- Performance tuning
- Security settings
- Logging configuration

## 📝 License

Open source - feel free to modify and distribute.

## 🤝 Contributing

Issues and pull requests welcome! See the code structure in `INTEGRATION_PLAN.md`.
