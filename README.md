# ProductBoard Insights

A reporting dashboard for ProductBoard notes with PM workload tracking, SLA monitoring, and Claude.ai MCP integration.

## Features

- **Dashboard**: Overview of notes, features, and key metrics
- **Notes Management**: View and filter notes with drill-down to details
- **Features Tracking**: Monitor features and linked notes
- **PM Workload**: Track workload distribution across team members
- **SLA Monitoring**: Track 5-day SLA compliance for note processing
- **Exports**: Generate PDF and JSON reports on-demand or scheduled
- **MCP Server**: Connect Claude.ai for ad-hoc analysis, investigation, and bulk operations via natural language

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, APScheduler
- **Frontend**: React, TypeScript, TanStack Query, Tailwind CSS
- **Database**: SQLite (fly.io persistent volume)
- **Deployment**: fly.io
- **MCP**: [Model Context Protocol](https://modelcontextprotocol.io) via `mcp[cli]`

## Quick Start

### Prerequisites

- Docker and Docker Compose
- ProductBoard API token

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd pdb-notes-insights
   ```

2. Create environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your ProductBoard API token and settings
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Run database migrations:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. Trigger initial data sync:
   ```bash
   curl -X POST http://localhost:8000/api/v1/sync/trigger
   ```

6. Access the application:
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs
   - Default login: admin / changeme

## Production Deployment

For production, use the production docker-compose:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Key differences:
- Frontend served on port 80
- No hot-reload or volume mounts
- Automatic restart on failure

## Configuration

See `.env.example` for all configuration options:

| Variable | Description | Default |
|----------|-------------|---------|
| PRODUCTBOARD_API_TOKEN | Your ProductBoard API token | (required) |
| DATABASE_URL | PostgreSQL connection string | postgresql://... |
| AUTH_USERNAME | Login username | admin |
| AUTH_PASSWORD | Login password | changeme |
| SYNC_INTERVAL_HOURS | Hours between syncs | 4 |
| EXPORT_SCHEDULE_HOUR | Hour for nightly exports (UTC) | 2 |
| MCP_API_KEY | Bearer token for MCP server auth (leave empty to disable) | (disabled) |

## MCP Server

The app exposes an MCP server at `/mcp` using the [Model Context Protocol](https://modelcontextprotocol.io) (Streamable HTTP transport). Connect Claude.ai to query and act on ProductBoard data via natural language.

### Connecting Claude.ai

1. Go to Claude.ai → Settings → Integrations → Add MCP Server
2. URL: `https://notes-hq.fly.dev/mcp`
3. Auth: Bearer token → paste your `MCP_API_KEY` value

### Available Tools (15)

**Query — Notes**
| Tool | Description |
|------|-------------|
| `list_notes` | Filter, sort, and group notes by owner/creator/company |
| `get_note` | Full note detail: content, linked features, comments |
| `search_notes` | Full-text search on title + content |
| `get_notes_stats` | All-time totals: total, processed, unprocessed, avg response time |
| `list_members` | All PMs/members with IDs and emails |
| `list_companies` | All companies with IDs |
| `list_features` | Features with linked note counts |

**Analytics — Reports**
| Tool | Description |
|------|-------------|
| `get_notes_insights` | Summary cards + owner performance table |
| `get_notes_trend` | Weekly created vs processed trend |
| `get_response_time_stats` | Distribution buckets + per-PM breakdown |
| `get_sla_report` | Breached / at-risk / on-track breakdown by owner |
| `get_pm_workload` | Unprocessed backlog per PM |

**Actions — Sync**
| Tool | Description |
|------|-------------|
| `trigger_sync` | Kick off a ProductBoard sync |
| `get_sync_status` | Check if sync is running, last completed time |
| `get_sync_history` | Last N sync runs with status and record counts |

### Enabling on fly.io

```bash
fly secrets set MCP_API_KEY=<your-token> --app notes-hq
fly deploy --app notes-hq
```

### Example Use Cases

- "Which companies have the most SLA-breached notes?"
- "Show me all unprocessed notes assigned to [PM] and summarize them"
- "Trigger a sync and tell me when it finishes"
- "What's the average response time trend over the last 30 days?"

## API Endpoints

- `POST /api/v1/auth/login` - Authenticate
- `GET /api/v1/notes` - List notes
- `GET /api/v1/features` - List features
- `GET /api/v1/reports/workload` - PM workload stats
- `GET /api/v1/reports/sla` - SLA compliance
- `POST /api/v1/exports` - Trigger export
- `GET /api/v1/scheduler/status` - Scheduler status

## Development

For local development without Docker:

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## License

MIT
