# 🤖 AI News Digest

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://hub.docker.com)
[![Python](https://img.shields.io/badge/Python-3.11+-green?logo=python)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-Frontend-blue?logo=typescript)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An AI-powered multi-type newsletter system that automatically ingests RSS feeds, generates intelligent summaries using multiple AI providers, and delivers professional newsletters via email. Perfect for businesses, content creators, and individuals who want to stay informed with personalized, AI-curated news digests.

**[View Sample Newsletter Output →](SAMPLE_OUTPUT.md)**

## ✨ Features

- ✅ **5 Newsletter Types**: General Business, Tech Focus, Market Pulse, General News, Industry Specific
- ✅ **Multi-AI Provider Support**: OpenAI GPT-5, Gemini, Anthropic Claude with automatic fallback
- ✅ **Intelligent Prompt Templates**: Newsletter-specific AI prompts with custom additions
- ✅ **Flexible Email Delivery**: Resend API or SMTP (Gmail, Outlook, corporate email servers)
- ✅ **Professional Formatting**: Clean markdown with market tables and visual indicators 🟢🔴
- ✅ **Modern Web Dashboard**: React-based interface for complete management
- ✅ **Docker Deployment**: One-command setup with docker-compose
- ✅ **RSS Feed Management**: Support for multiple feeds with categorization
- ✅ **Scheduling System**: Automated daily/weekly newsletters with timezone support
- ✅ **Market Data Integration**: Stock quotes and financial data for market-focused newsletters
- ✅ **Customizable Verbosity**: Control AI response length and detail level
- ✅ **Health Monitoring**: Built-in system health checks and logging

## 📋 Prerequisites

Before you begin, ensure you have:

- **Docker & Docker Compose** (recommended) OR Python 3.11+ and Node.js 18+
- **At least one AI provider API key**:
  - [OpenAI API Key](https://platform.openai.com/api-keys) (recommended - supports verbosity control)
  - [Google Gemini API Key](https://makersuite.google.com/app/apikey) (backup option)
  - [Anthropic Claude API Key](https://console.anthropic.com/) (backup option)
- **Email service** (choose one):
  - [Resend Account](https://resend.com) (recommended - simple setup)
  - SMTP credentials (Gmail, Outlook, corporate email)

## 🚀 Quick Start (5 minutes)

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
RESEND_FROM_EMAIL="newsletters@yourdomain.com"

# Optional: Customize settings
PORT=8000
DEFAULT_TIMEZONE="America/New_York"
APP_NAME="My News Digest"
```

### 3. Deploy with Docker
```bash
docker-compose up -d
```

### 4. Access Dashboard
Visit `http://localhost:8000` and:
1. Create your first newsletter
2. Add RSS feeds (news sources)
3. Configure schedule and recipients
4. Send test newsletter

## 📧 Email Configuration Options

### Option 1: Resend (Recommended)
Simple API-based email delivery with excellent deliverability:
```env
RESEND_API_KEY="re_your-key-here"
RESEND_FROM_EMAIL="newsletters@yourdomain.com"
RESEND_FROM_NAME="My News Digest"
```

### Option 2: SMTP (Gmail, Outlook, Corporate)
Use your existing email infrastructure:
```env
EMAIL_BACKEND="smtp"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"  # Use app password for Gmail
SMTP_USE_TLS=true
```

**Popular SMTP Settings:**
- **Gmail**: `smtp.gmail.com:587` (requires app password)
- **Outlook**: `smtp-mail.outlook.com:587`
- **Yahoo**: `smtp.mail.yahoo.com:587`

## 📊 Newsletter Types Explained

| Type | Focus | Best For | Sample Topics |
|------|-------|----------|---------------|
| **General Business** | Corporate strategy, economics | Business professionals, executives | M&A, earnings, economic indicators |
| **Tech Focus** | Technology innovation, startups | Developers, tech workers | AI developments, startup funding, product launches |
| **Market Pulse** | Financial markets, trading | Investors, traders | Stock movements, Fed policy, market analysis |
| **General News** | Comprehensive current events | General audience | Politics, world events, social issues |
| **Industry Specific** | Sector-focused coverage | Industry professionals | Healthcare, energy, automotive (customizable) |

## 🔧 Advanced Configuration

### Custom Port and Host
```env
PORT=3000
HOST=0.0.0.0
```

### Performance Tuning
```env
MAX_CONCURRENT_FEEDS=5
REQUEST_TIMEOUT=30.0
MAX_ARTICLES_PER_FEED=10
```

### Multiple Recipients
```env
DEFAULT_RECIPIENTS="user1@company.com,user2@company.com,team@company.com"
```

## 🐳 Alternative Deployment Methods

### Option A: Docker Build (Advanced)
```bash
docker build -t ai-news-digest .
docker run --env-file .env -p 8000:8000 ai-news-digest
```

### Option B: Local Development
```bash
# Install Python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build frontend
cd frontend && npm install && npm run build && cd ..

# Initialize database and start
.venv/bin/python -m app.tasks.prestart
.venv/bin/uvicorn app.web.main:app --reload
```

### Option C: Production Server
For production deployment, consider:
- Using a reverse proxy (nginx)
- SSL/TLS certificates
- Environment-specific configuration
- Backup strategies for the SQLite database

## 🛠 Troubleshooting

### Common Issues

**🔴 "Newsletter generation failed"**
- Check AI provider API keys are valid and have credits
- Verify RSS feeds are accessible (test URLs in browser)
- Review logs in the Health & Logs section

**🔴 "Email delivery failed"**
- Verify email configuration (Resend API key or SMTP settings)
- Check recipient email addresses are valid
- For Gmail SMTP: ensure you're using an app password, not your regular password

**🔴 "Container won't start"**
- Ensure Docker is running: `docker --version`
- Check port availability: `lsof -i :8000`
- Verify .env file exists and has required keys

**🔴 "Cannot access dashboard"**
- Wait 30-60 seconds after `docker-compose up` for full startup
- Check container logs: `docker-compose logs`
- Verify port in browser matches PORT in .env

### Getting Help

1. **Check container logs**: `docker-compose logs ai-news-digest`
2. **Verify health**: Visit `http://localhost:8000/api/status/health`
3. **Review configuration**: Ensure all required environment variables are set

## ❓ Frequently Asked Questions

**Q: How much does it cost to run?**
A: Costs depend on usage:
- OpenAI: ~$0.01-0.05 per newsletter (varies by length)
- Resend: 3,000 emails free/month, then $0.50/1000
- Infrastructure: Free with Docker on your server

**Q: Can I customize the AI prompts?**
A: Yes! Each newsletter has:
- A pre-built template for its type (Business, Tech, etc.)
- Custom prompt field for your specific requirements
- Global prompt modifications in the codebase

**Q: How do I add more RSS feeds?**
A: In the dashboard:
1. Edit your newsletter
2. Add feed URLs in the "Feeds" section
3. Optionally categorize and title each feed

**Q: Can I send to multiple people?**
A: Absolutely:
- Set default recipients in .env: `DEFAULT_RECIPIENTS="email1,email2"`
- Override per newsletter in the dashboard
- Support for mailing lists and distribution groups

**Q: What if an AI provider is down?**
A: The system automatically falls back to other configured providers (OpenAI → Gemini → Anthropic)

**Q: How do I backup my data?**
A: Your data is in the `./data/` folder:
```bash
# Backup
cp -r data/ backup-$(date +%Y%m%d)/

# Restore
cp -r backup-20241201/ data/
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Quick Contributions
- 🐛 **Report bugs**: [Open an issue](https://github.com/jsnider89/ai-news-digest/issues)
- 💡 **Suggest features**: [Feature request template](https://github.com/jsnider89/ai-news-digest/issues)
- 📖 **Improve docs**: Submit PRs for README improvements

### Development Setup
```bash
git clone https://github.com/jsnider89/ai-news-digest.git
cd ai-news-digest

# Backend development
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend development
cd frontend
npm install
npm run dev  # Hot reload for UI changes
```

### Code Structure
- **`app/`** - Python backend (FastAPI, AI integration, email)
- **`frontend/`** - TypeScript React dashboard
- **`app/prompts/`** - AI prompt templates (easy to modify)
- **`docker/`** - Container configuration

### Pull Request Guidelines
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with clear commit messages
4. Test locally with `docker-compose up`
5. Submit a pull request with a clear description

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Documentation**: This README and inline code comments
- **Sample Output**: [View example newsletters](SAMPLE_OUTPUT.md)
- **Issues**: [Report bugs or request features](https://github.com/jsnider89/ai-news-digest/issues)
- **Discussions**: [Community discussions](https://github.com/jsnider89/ai-news-digest/discussions)

---

**Built with ❤️ using FastAPI, React, and AI**

*AI News Digest - Stay informed, stay ahead*
