# ProductBoard Notes Reporting System - Design Document

**Date:** 2026-01-16
**Status:** Approved

## Overview

A read-only reporting system for ProductBoard notes that provides:
- Web dashboard with interactive charts and drill-down navigation
- Scheduled exports (PDF + JSON) nightly
- Management reports for PM workload and SLA tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│  (Dashboard UI, Charts, Filters, Export Triggers)               │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP/REST
┌─────────────────────────▼───────────────────────────────────────┐
│                     FastAPI Backend                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Report APIs │  │ Sync Engine │  │ Export Service          │  │
│  │ (read-only) │  │ (scheduler) │  │ (PDF/JSON generation)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                      PostgreSQL                                 │
│  (Notes, Features, Customers, Sync History)                     │
└─────────────────────────────────────────────────────────────────┘
                          ▲
                          │ Periodic Sync + On-demand
┌─────────────────────────┴───────────────────────────────────────┐
│                   ProductBoard API v2                           │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

- **React Frontend**: Single-page app with charts, tables, filters. Calls FastAPI for all data.
- **FastAPI Backend**: Three main services - Report APIs for dashboard queries, Sync Engine for ProductBoard data pulls, Export Service for nightly PDF/JSON generation.
- **PostgreSQL**: Stores synced data locally. Enables fast queries and historical comparisons.

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Recharts/Chart.js, TanStack Table, TanStack Query, React Router, Tailwind CSS |
| Backend | Python, FastAPI, SQLAlchemy, Alembic, APScheduler, httpx, WeasyPrint |
| Database | PostgreSQL 15 |
| Deployment | Docker Compose (local), flexible for cloud |

## Data Model

### Notes

```sql
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    pb_id VARCHAR UNIQUE NOT NULL,
    title VARCHAR,
    content TEXT,
    type VARCHAR,                    -- simple, conversation, opportunity
    source VARCHAR,
    state VARCHAR,                   -- processed, unprocessed
    processed_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    creator_id INTEGER REFERENCES users(id),
    owner_id INTEGER REFERENCES users(id),
    team_id INTEGER REFERENCES teams(id),
    customer_id INTEGER REFERENCES customers(id),
    custom_fields JSONB,
    synced_at TIMESTAMP
);
```

### Features

```sql
CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    pb_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    description TEXT,
    type VARCHAR,                    -- feature, subfeature
    status VARCHAR,
    component_id INTEGER REFERENCES components(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    creator_id INTEGER REFERENCES users(id),
    owner_id INTEGER REFERENCES users(id),
    team_id INTEGER REFERENCES teams(id),
    -- Custom fields (known)
    product_area VARCHAR,
    product_area_stack_rank INTEGER,
    committed BOOLEAN,
    risk VARCHAR,
    tech_lead_id INTEGER REFERENCES users(id),
    -- Extensibility
    custom_fields JSONB,
    synced_at TIMESTAMP
);
```

### Customers

```sql
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    pb_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    email VARCHAR,
    company_id INTEGER REFERENCES companies(id),
    created_at TIMESTAMP,
    synced_at TIMESTAMP
);
```

### Companies

```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    pb_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    domain VARCHAR,
    -- Custom fields
    customer_id VARCHAR,             -- Internal customer ID
    account_sales_theatre VARCHAR,
    cse VARCHAR,                     -- Customer Success Engineer
    arr DECIMAL,                     -- Annual Recurring Revenue
    account_type VARCHAR,
    contract_start_date DATE,
    contract_end_date DATE,
    synced_at TIMESTAMP
);
```

### Users

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    pb_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    email VARCHAR,
    role VARCHAR,
    synced_at TIMESTAMP
);
```

### Teams

```sql
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    pb_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    synced_at TIMESTAMP
);
```

### Components

```sql
CREATE TABLE components (
    id SERIAL PRIMARY KEY,
    pb_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    parent_id INTEGER REFERENCES components(id),
    synced_at TIMESTAMP
);
```

### Relationships

```sql
CREATE TABLE note_features (
    note_id INTEGER REFERENCES notes(id),
    feature_id INTEGER REFERENCES features(id),
    linked_at TIMESTAMP,
    PRIMARY KEY (note_id, feature_id)
);

CREATE TABLE feature_customers (
    feature_id INTEGER REFERENCES features(id),
    customer_id INTEGER REFERENCES customers(id),
    source VARCHAR,                  -- direct, via_note, inferred
    note_count INTEGER,
    PRIMARY KEY (feature_id, customer_id)
);
```

### Sync History

```sql
CREATE TABLE sync_history (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR,                  -- running, completed, partial, failed
    records_synced INTEGER,
    error_message TEXT
);
```

## Dashboard & Reports

### Main Dashboard (Home)

- Total notes, features, customers, companies (summary cards)
- Notes trend over time (line chart - last 30/90/365 days)
- Notes by status: linked vs unlinked to features (donut chart)
- Recent sync status indicator

### Notes Reports

| Report | Visualization |
|--------|---------------|
| Notes over time | Line/area chart with filters (source, type, team) |
| Notes by source | Bar chart (e.g., Intercom, Zendesk, manual) |
| Notes by type | Donut chart (simple, conversation, opportunity) |
| Notes by team/owner | Bar chart with drill-down |
| Unlinked notes | Table with search/filter - notes not connected to any feature |
| Note detail view | Single note with linked features, customer info, metadata |

### Features Reports

| Report | Visualization |
|--------|---------------|
| Features by note count | Bar chart - most requested features |
| Features by Product Area | Grouped bar chart |
| Features by Stack Rank | Sortable table with note counts |
| Committed vs Uncommitted | Donut chart with note breakdown |
| Features by Risk | Heatmap or grouped bars |
| Features by Tech Lead | Workload distribution |
| Feature detail view | Single feature with all linked notes, customers, metadata |

### PM Workload Dashboard (Management)

| Report | Visualization |
|--------|---------------|
| Notes by PM | Stacked bar (processed vs unprocessed per PM) |
| Processing rate by PM | Bar chart (% processed) |
| Unprocessed backlog by PM | Table with count and oldest note age |
| Features owned by PM | Bar chart with note counts |

### SLA Tracking Dashboard (Management)

| Report | Visualization |
|--------|---------------|
| SLA compliance rate | Gauge/KPI card (% processed within 5 days) |
| SLA compliance trend | Line chart over time |
| SLA compliance by PM | Bar chart (% within SLA per PM) |
| SLA breaches | Table: notes that took >5 days, grouped by PM |
| At-risk notes | Table: unprocessed notes approaching 5-day threshold (3-4 days old) |
| Average processing time | KPI card overall + breakdown by PM |
| Processing time distribution | Histogram (days to process) |

### Customer & Company Reports

| Report | Visualization |
|--------|---------------|
| Top customers by note count | Bar chart |
| Companies by ARR | Sortable table with note/feature counts |
| Companies by theatre | Grouped view |
| Customer detail | All notes, features, company info |
| Company detail | All contacts, aggregated notes/features, contract info |

## Drill-Down Behavior

All reports are interactive with full drill-down capability.

### Charts → Filtered Tables

| Click on... | Navigates to... |
|-------------|-----------------|
| Bar segment (e.g., PM "Alice") | Notes table filtered to owner=Alice |
| Donut slice (e.g., "Unprocessed") | Notes table filtered to state=unprocessed |
| Line chart point (e.g., March 15) | Notes table filtered to created_at=March 15 |
| Product Area group | Features table filtered to that Product Area |
| SLA breach count | Notes table: only notes >5 days to process |
| Customer/Company in chart | Customer/Company detail view |

### Tables → Detail Views

| Click on... | Opens... |
|-------------|----------|
| Note row | Note detail view |
| Feature row | Feature detail view |
| PM/User name | PM profile with stats |
| Customer name | Customer detail |
| Company name | Company detail |

### Breadcrumb Navigation

All drill-downs maintain a breadcrumb trail:
```
Dashboard > Notes by PM > Alice > Note #1234
```

## API Design

**Base URL:** `/api/v1`

### Authentication

```
POST /auth/login          → Returns session token
POST /auth/logout         → Invalidates session
GET  /auth/me             → Current user info
```

### Notes

```
GET  /notes               → List notes (paginated, filterable)
GET  /notes/:id           → Single note with relationships
GET  /notes/stats         → Aggregate stats (counts, trends)
GET  /notes/sla           → SLA metrics (compliance, breaches)
```

### Features

```
GET  /features            → List features (paginated, filterable)
GET  /features/:id        → Single feature with linked notes/customers
GET  /features/stats      → Aggregate stats
```

### Customers & Companies

```
GET  /customers           → List customers
GET  /customers/:id       → Single customer with notes/features
GET  /companies           → List companies
GET  /companies/:id       → Single company with rollup stats
GET  /companies/stats     → Aggregate by theatre, ARR tier
```

### Users & Teams

```
GET  /users               → List users
GET  /users/:id           → Single user with workload stats
GET  /users/:id/stats     → PM-specific metrics
GET  /teams               → List teams
GET  /teams/:id           → Team with aggregate stats
```

### Sync Management

```
POST /sync/trigger        → Trigger on-demand sync
GET  /sync/status         → Current sync status
GET  /sync/history        → Past sync runs
```

### Exports

```
POST /exports             → Trigger export
GET  /exports             → List past exports
GET  /exports/:id         → Download specific export
```

### Common Query Parameters

```
?page=1&limit=50                    → Pagination
?sort=created_at&order=desc         → Sorting
?state=unprocessed                  → Filter by field
?owner_id=123                       → Filter by PM
?product_area=Platform              → Filter by product area
?created_after=2024-01-01           → Date range
?created_before=2024-03-01
?theatre=EMEA                       → Filter by sales theatre
?arr_min=100000                     → Filter by ARR
```

## Sync Engine

### Sync Strategy

- **Scheduled**: Every 4 hours (configurable)
- **On-demand**: Manual trigger via API/UI

### Sync Order

1. Users & Teams (no dependencies)
2. Companies (no dependencies)
3. Customers (depends on companies)
4. Components (no dependencies)
5. Features (depends on components, users, teams)
6. Notes (depends on customers, users, teams)
7. Relationships (depends on notes, features, customers)

### Incremental Sync Logic

```python
# For each entity type:
1. Fetch from ProductBoard API with ?updated_after=last_sync_time
2. Upsert into PostgreSQL (insert or update based on pb_id)
3. Track deleted records (soft delete or flag missing)
4. Update sync_history with results
```

### Rate Limiting

- ProductBoard limit: 50 req/sec
- Implementation: Token bucket with 40 req/sec target (safety margin)
- Backoff on 429 responses

### Error Handling

| Scenario | Behavior |
|----------|----------|
| API timeout | Retry 3x with exponential backoff |
| Rate limited (429) | Pause, wait for reset, continue |
| Partial failure | Log error, continue with other entities, mark sync as "partial" |
| Auth failure | Stop sync, alert, require manual intervention |

### Custom Fields Handling

1. On first sync: GET /configuration/custom-fields
2. Store field definitions (id, name, type, options)
3. Map known fields to columns, rest to JSONB
4. Re-fetch field definitions weekly

## Export Service

### Export Types

| Report | PDF | JSON |
|--------|-----|------|
| Notes Summary | ✓ | ✓ |
| Features Summary | ✓ | ✓ |
| PM Performance | ✓ | ✓ |
| SLA Report | ✓ | ✓ |
| Customer Insights | ✓ | ✓ |
| Full Data Dump | - | ✓ |

### Scheduled Exports

- Runs nightly at configured time (default: 2:00 AM)
- Saves to `/exports/{date}/{report-name}.{pdf|json}`
- Optional email delivery to configured recipients
- Retention: 30 days (configurable)

### PDF Generation

- Library: WeasyPrint or ReportLab
- Template-based: HTML/CSS templates rendered to PDF
- Charts embedded as images (matplotlib/plotly)

### JSON Structure

```json
{
  "report": "pm_performance",
  "generated_at": "2024-03-15T02:00:00Z",
  "period": { "from": "2024-03-01", "to": "2024-03-14" },
  "data": {
    "summary": { ... },
    "by_pm": [ ... ],
    "sla_metrics": { ... }
  }
}
```

## Project Structure

```
pdb-notes-insights/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Settings, env vars
│   │   ├── database.py             # PostgreSQL connection
│   │   │
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── note.py
│   │   │   ├── feature.py
│   │   │   ├── customer.py
│   │   │   ├── company.py
│   │   │   ├── user.py
│   │   │   └── ...
│   │   │
│   │   ├── api/                    # API routes
│   │   │   ├── notes.py
│   │   │   ├── features.py
│   │   │   ├── customers.py
│   │   │   ├── users.py
│   │   │   ├── sync.py
│   │   │   └── exports.py
│   │   │
│   │   ├── services/               # Business logic
│   │   │   ├── sync/
│   │   │   │   ├── orchestrator.py
│   │   │   │   ├── notes_syncer.py
│   │   │   │   ├── features_syncer.py
│   │   │   │   └── ...
│   │   │   ├── reports/
│   │   │   │   ├── notes_stats.py
│   │   │   │   ├── sla_metrics.py
│   │   │   │   └── ...
│   │   │   └── exports/
│   │   │       ├── pdf_generator.py
│   │   │       └── json_generator.py
│   │   │
│   │   ├── integrations/           # External API clients
│   │   │   └── productboard/
│   │   │       ├── client.py
│   │   │       ├── notes.py
│   │   │       ├── features.py
│   │   │       └── ...
│   │   │
│   │   └── scheduler/              # APScheduler jobs
│   │       ├── sync_job.py
│   │       └── export_job.py
│   │
│   ├── alembic/                    # Database migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   ├── tables/
│   │   │   ├── filters/
│   │   │   └── layout/
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Notes.tsx
│   │   │   ├── Features.tsx
│   │   │   ├── Customers.tsx
│   │   │   ├── Management.tsx
│   │   │   └── Settings.tsx
│   │   │
│   │   ├── hooks/
│   │   ├── api/
│   │   └── types/
│   │
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

## Configuration

### Environment Variables

```bash
# ProductBoard API
PRODUCTBOARD_API_TOKEN=your_api_token
PRODUCTBOARD_API_URL=https://api.productboard.com

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/pdb_insights

# Auth
AUTH_USERNAME=admin
AUTH_PASSWORD=securepassword
SESSION_SECRET=random_secret_key

# Sync
SYNC_INTERVAL_HOURS=4
SYNC_ENABLED=true

# Exports
EXPORT_SCHEDULE_HOUR=2
EXPORT_RETENTION_DAYS=30
EXPORT_PATH=/app/exports

# Optional: Email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EXPORT_EMAIL_RECIPIENTS=team@example.com
```

### Docker Compose

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/pdb_insights
    depends_on:
      - db
    volumes:
      - ./exports:/app/exports

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: pdb_insights
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  pgdata:
```

### Running Locally

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Trigger initial sync
curl -X POST http://localhost:8000/api/v1/sync/trigger

# Access
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

## Summary

| Aspect | Decision |
|--------|----------|
| **Stack** | Python (FastAPI) + React (TypeScript) + PostgreSQL |
| **Data Strategy** | Local cache, sync every 4 hours + on-demand |
| **Auth** | Simple shared password for small team |
| **Exports** | PDF + JSON, nightly at 2 AM |
| **Deployment** | Docker Compose, start local, flexible for cloud |

### Core Reports

- **Notes**: volume, trends, by source/type/team, unlinked notes
- **Features**: by note count, product area, stack rank, risk, tech lead
- **Customers/Companies**: by ARR, theatre, feedback volume
- **Management**: PM workload, processing rates, SLA compliance/breaches

### Key Capabilities

- Bidirectional note ↔ feature relationships
- Customer insights at contact and company level
- 5-day SLA tracking with at-risk alerts
- Full drill-down from any chart to underlying data
- Custom field extensibility (JSONB)
