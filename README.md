# AI News Digest

An intelligent newsletter aggregator that uses AI to curate and summarize news from multiple RSS feeds. Configure custom newsletters, schedule automated digests, and deliver professionally formatted emails to your subscribers.

## Features

- **AI-Powered Analysis**: Uses OpenAI, Google Gemini, or Anthropic Claude to generate intelligent summaries
- **Multi-Provider Fallback**: Automatically switches between AI providers if one fails
- **Multiple Newsletters**: Create and manage different newsletters with custom RSS feeds
- **Flexible Scheduling**: Schedule newsletters at specific times with timezone support
- **Web Admin Interface**: Modern React-based UI for configuration and monitoring
- **Email Delivery**: Send newsletters via Resend or SMTP
- **Market Data Integration**: Optional integration with Finnhub for financial market data
- **Docker-Based Deployment**: Easy deployment with Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- At least one AI API key (OpenAI, Gemini, or Anthropic)
- Resend API key for email delivery (or SMTP credentials)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jsnider89/ai-news-digest.git
   cd ai-news-digest
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API keys:
   - **Required**: At least one AI provider API key (OpenAI, Gemini, or Anthropic)
   - **Required**: Resend API key or SMTP credentials
   - **Optional**: Finnhub API key for market data
   - Update `DEFAULT_RECIPIENTS` with your email address
   - Set `DEFAULT_TIMEZONE` to your timezone

3. **Start the application**
   ```bash
   docker compose up -d
   ```

4. **Access the web interface**

   Open your browser to `http://localhost:8002`

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# AI Provider (at least one required)
OPENAI_API_KEY="your_key_here"
GEMINI_API_KEY="your_key_here"
ANTHROPIC_API_KEY="your_key_here"

# Email Configuration
RESEND_API_KEY="your_key_here"
RESEND_FROM_EMAIL="digest@yourdomain.com"
DEFAULT_RECIPIENTS="your-email@example.com"

# Application Settings
DEFAULT_TIMEZONE="America/Denver"
DEFAULT_SEND_TIMES="06:30,17:30"
```

See `.env.example` for all available options.

### Creating Newsletters

1. Access the web interface at `http://localhost:8002`
2. Navigate to the Newsletters section
3. Click "Create Newsletter"
4. Configure:
   - Newsletter name
   - RSS feed URLs
   - Schedule times
   - Newsletter type (General, Tech, Market, etc.)
5. Save and activate

## API Endpoints

- `GET /health` - Health check
- `GET /api/newsletters` - List all newsletters
- `POST /api/newsletters` - Create a newsletter
- `GET /api/runs` - View newsletter run history
- `GET /api/settings` - View application settings
- `PUT /api/settings` - Update settings

## Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.web.main:app --reload --port 8002
```

### Project Structure

```
.
├── app/
│   ├── ai/          # AI provider integrations
│   ├── config/      # Configuration management
│   ├── data/        # Database models and repositories
│   ├── email/       # Email rendering and delivery
│   ├── ingest/      # RSS feed ingestion
│   ├── tasks/       # Background task scheduling
│   ├── utils/       # Utility functions
│   └── web/         # FastAPI web application
├── config/          # Configuration files
├── data/            # Database and persistent data
├── docker/          # Docker-related files
├── frontend/        # React admin interface
└── requirements.txt # Python dependencies
```

## Troubleshooting

### Container won't start
- Check Docker logs: `docker compose logs ai-news-digest`
- Ensure all required environment variables are set in `.env`
- Verify port 8002 is not already in use

### Newsletters not sending
- Check API keys are valid
- Verify Resend domain is configured and verified
- Review logs at `http://localhost:8002` (Logs section)
- Check email recipient addresses are correct

### AI generation fails
- Ensure at least one AI provider API key is valid
- Check provider API quotas and billing
- Review error messages in run logs

## Getting API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Google Gemini**: https://aistudio.google.com/app/apikey
- **Anthropic**: https://console.anthropic.com/
- **Resend**: https://resend.com
- **Finnhub** (optional): https://finnhub.io

## License

This project is provided as-is for personal and commercial use.

## Support

For issues, questions, or contributions, please open an issue on GitHub.
