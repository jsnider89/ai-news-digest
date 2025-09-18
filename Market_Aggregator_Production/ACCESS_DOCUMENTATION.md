# Git and Wrangler Access Documentation

## Git Access
**Current Status**: Using standard git commands from the project directory
- Working from: `/home/administrator/projects/marketaggregator`
- Repository is already initialized and has a clean working tree
- Standard git workflow:
  ```bash
  git status          # Check repository status
  git diff            # View unstaged changes
  git add .           # Stage changes
  git commit -m "..."  # Commit changes
  git push            # Push to remote repository
  ```

## Wrangler CLI Access
**Authentication**: Already authenticated with OAuth token
- Account: jonsnider@hotmail.com
- Account ID: `27dd92b3ccbe83f4f08ee24bbf0711be`
- Token has full permissions including workers, KV, D1, pages, etc.

**Working Directory**: `/home/administrator/projects/marketaggregator/apps/worker`

**Key Commands**:
```bash
# Check authentication
wrangler whoami

# List resources
wrangler d1 list
wrangler kv namespace list
wrangler secret list

# Worker management
wrangler deployments list
wrangler deploy

# Database operations
wrangler d1 info ai_market_intel_db
wrangler d1 execute ai_market_intel_db --file=../../db/schema.sql

# Secret management
wrangler secret put RESEND_API_KEY
wrangler secret put GEMINI_API_KEY
```

**For Your Coder to Set Up**:
1. Install wrangler: `npm install -g wrangler`
2. Login: `wrangler login` (will open browser for OAuth)
3. Navigate to worker directory: `cd apps/worker`
4. Verify access: `wrangler whoami`

**Current Configuration**:
- Worker: `ai-market-intel-worker`
- D1 Database: `ai_market_intel_db` (ID: 87fe856f-59b3-4548-8b38-2e15bca4e738)
- KV Namespace: `MARKET_FLAGS` (ID: fa6e9f8229d64507af061fdce39c6195)
- Secrets: `GEMINI_API_KEY`, `RESEND_API_KEY` already configured