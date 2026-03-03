# MCP Server Design

**Date:** 2026-03-02
**Status:** Approved

## Overview

Add an MCP (Model Context Protocol) server to the Notes HQ app so that Claude.ai can interactively query and act on ProductBoard data — covering all the use cases the webapp solves, plus ad-hoc analysis, investigation workflows, and bulk operations the UI doesn't support.

## Architecture

### Approach
- MCP server mounted as an **ASGI sub-app within FastAPI** at `/mcp`
- Lives in a new `backend/mcp/` module — completely separate from the REST API
- **Direct SQLAlchemy DB access** — imports models from `app.models`, no HTTP hop
- No changes to fly.io config — runs on the same port 8000 under `force_https = true`

### Transport
- **Streamable HTTP** (MCP 2025-03-26 spec)
- Claude.ai connects to: `https://notes-hq.fly.dev/mcp`

### Authentication
- **Static Bearer token** checked in middleware
- Configured via `MCP_API_KEY` env var in fly.io secrets
- All requests without a valid token return 401

### Data Flow
```
Claude.ai → HTTPS → fly.io → FastAPI (port 8000)
                               ├── /api/...   existing REST (unchanged)
                               └── /mcp       MCP sub-app
                                     └── SQLAlchemy → SQLite (/data/pdb_insights.db)
```

## File Structure

```
backend/mcp/
  __init__.py
  server.py          ← MCP app setup, tool registration, ASGI app export
  auth.py            ← Bearer token middleware
  tools/
    __init__.py
    notes.py         ← note query & search tools
    reports.py       ← analytics tools
    sync.py          ← sync action tools
```

**Existing file change** — add 2 lines to `backend/app/main.py`:
```python
from mcp.server import mcp_app
app.mount("/mcp", mcp_app)
```

## Tools (14 total)

### Query Tools — Notes
| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_notes` | `state`, `owner_id`, `creator_id`, `company_id`, `created_after`, `created_before`, `sort`, `order`, `group_by` (`owner`\|`creator`\|`company`), `page`, `limit` | Filter, sort, and group notes |
| `get_note` | `note_id` | Full note detail: content, linked features, comments, response time |
| `search_notes` | `query`, `state`, `page`, `limit` | Full-text search on title + content |
| `get_notes_stats` | — | All-time totals: total, processed, unprocessed, avg response time |
| `list_members` | — | All PMs/members with IDs and emails |
| `list_companies` | — | All companies with IDs |
| `list_features` | — | Features with linked note counts |

### Analytics Tools — Reports
| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_notes_insights` | `days` | Summary cards + owner performance table (mirrors Insights page) |
| `get_notes_trend` | `days` | Weekly created vs processed trend |
| `get_response_time_stats` | `days` | Distribution buckets + per-PM breakdown |
| `get_sla_report` | `days` | Breached / at-risk / on-track breakdown by owner |
| `get_pm_workload` | — | Unprocessed backlog per PM |

### Action Tools — Sync
| Tool | Parameters | Description |
|------|-----------|-------------|
| `trigger_sync` | — | Kick off a ProductBoard sync |
| `get_sync_status` | — | Check if sync is running, last completed time |
| `get_sync_history` | `limit` | Last N sync runs with status and record counts |

## Dependencies

```
# backend/requirements.txt — add:
mcp[cli]>=1.0.0
```

## Deployment

1. Add `mcp[cli]` to `backend/requirements.txt`
2. Implement `backend/mcp/` module
3. Mount in `backend/app/main.py`
4. Set secret: `fly secrets set MCP_API_KEY=<token>`
5. Deploy: `fly deploy`

## Connecting Claude.ai

1. Go to Claude.ai → Settings → Integrations → Add MCP Server
2. URL: `https://notes-hq.fly.dev/mcp`
3. Auth: Bearer token → paste `MCP_API_KEY` value

## Use Cases Enabled

- **Ad-hoc analysis**: "Which companies have the most SLA-breached notes?"
- **Investigation**: Drill into a PM's backlog, understand patterns, get recommendations
- **Bulk operations**: "Find all notes from Acme Corp and summarize them"
- **All Insights page views**: Summary, trend, response time distribution, owner performance
- **All SLA views**: Breached, at-risk, by-owner breakdown
- **Actions**: Trigger syncs on demand, monitor sync health
