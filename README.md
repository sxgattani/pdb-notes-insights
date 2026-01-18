# ProductBoard Insights

A read-only reporting dashboard for ProductBoard notes with PM workload tracking, SLA monitoring, and scheduled exports.

## Features

- **Dashboard**: Overview of notes, features, and key metrics
- **Notes Management**: View and filter notes with drill-down to details
- **Features Tracking**: Monitor features and linked notes
- **PM Workload**: Track workload distribution across team members
- **SLA Monitoring**: Track 5-day SLA compliance for note processing
- **Exports**: Generate PDF and JSON reports on-demand or scheduled

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, APScheduler
- **Frontend**: React, TypeScript, TanStack Query, Tailwind CSS
- **Database**: PostgreSQL 15
- **Containerization**: Docker, Docker Compose

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
