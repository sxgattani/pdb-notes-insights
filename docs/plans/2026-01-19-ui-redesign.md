# UI Redesign Plan for PM Leadership Analytics

**Date:** 2026-01-19
**Audience:** PM Leadership
**Focus:** Team performance, SLA compliance, workload distribution, response times

---

## Executive Summary

Redesign the UI to align with the new data model (Member, Company, Note, NoteComment, Feature) and optimize for PM Leadership analytics. Remove deprecated pages, fix backend APIs, and add response time metrics.

---

## Navigation Structure

**New (5 pages):**
```
Dashboard | Notes | Insights | SLA | Exports
```

**Removed:**
- FeaturesListPage - Features are now just references from notes
- FeatureDetailPage - No independent feature management needed
- WorkloadPage - Merged into Insights page

---

## Phase 1: Backend API Fixes

### 1.1 Update `backend/app/api/notes.py`

| Change | Details |
|--------|---------|
| Import | `User` → `Member` |
| Remove filter | `customer_id` parameter and filter |
| Remove field | `Note.type` references |
| Rename field | `Note.source` → `Note.source_origin` |
| Fix relationships | Query `Member` instead of `User` for owner/creator |
| Add field | Include `Note.source_origin`, `Note.tags`, `Note.followers_count`, `Note.processed_at` in response |

**Updated `_note_to_dict` function should include:**
```python
{
    "id": note.id,
    "pb_id": note.pb_id,
    "title": note.title,
    "content": note.content,
    "state": note.state,
    "source_origin": note.source_origin,
    "display_url": note.display_url,
    "external_display_url": note.external_display_url,
    "tags": note.tags or [],
    "followers_count": note.followers_count,
    "created_at": note.created_at.isoformat() if note.created_at else None,
    "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    "processed_at": note.processed_at.isoformat() if note.processed_at else None,
    "response_time_days": calculate_response_time(note),  # NEW
    "owner": {...},  # from Member model
    "creator": {...},  # from Member model (created_by_id)
    "company": {...},
}
```

**Add response time calculation:**
```python
def calculate_response_time(note: Note) -> Optional[float]:
    """Calculate response time in days (processed_at - created_at)."""
    if note.processed_at and note.created_at:
        delta = note.processed_at - note.created_at
        return round(delta.total_seconds() / 86400, 1)  # Convert to days
    return None
```

### 1.2 Update `backend/app/api/reports.py`

| Change | Details |
|--------|---------|
| Import | `User` → `Member` |
| All queries | Replace `User` joins with `Member` joins |
| `Note.source` | Change to `Note.source_origin` |
| Add endpoint | `/reports/response-time` for response time analytics |

**New endpoint: `/reports/response-time`**
```python
@router.get("/response-time")
def get_response_time_stats(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get response time analytics."""
    # Returns:
    # - average_days: float
    # - median_days: float
    # - distribution: [{bucket: "<1 day", count: 45}, ...]
    # - by_owner: [{name, avg_response_time, count}, ...]
    # - trend: [{week, avg_response_time}, ...]  # weekly trend
```

**Update `/reports/notes-insights` to include:**
- `avg_response_time` in summary stats
- `avg_response_time` column in by_maker (rename to by_owner)
- `sla_breached` count per owner

### 1.3 Update `backend/app/api/exports.py`

Update report generation to use new model fields.

---

## Phase 2: Frontend - Remove Deprecated Pages

### 2.1 Delete Files
- `frontend/src/pages/FeaturesListPage.tsx`
- `frontend/src/pages/FeatureDetailPage.tsx`
- `frontend/src/pages/WorkloadPage.tsx`
- `frontend/src/components/FeaturesTable.tsx`
- `frontend/src/api/features.ts`

### 2.2 Update `frontend/src/App.tsx`
- Remove imports for deleted pages
- Remove routes for `/features`, `/features/:id`, `/workload`
- Remove "Features" and "Workload" from navigation

---

## Phase 3: Dashboard Redesign

### 3.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ProductBoard Insights                    [Sync from ProductBoard] │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│ │  Total   │ │Processed │ │Unprocessed│ │  Avg Response Time  │ │
│ │  Notes   │ │   85%    │ │          │ │      2.3 days       │ │
│ │  2,472   │ │  2,101   │ │   371    │ │                     │ │
│ └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────┐ ┌────────────────────────────┐   │
│ │    Notes by Owner          │ │     SLA Status             │   │
│ │ ┌─────────────────────────┐│ │      ┌─────────┐           │   │
│ │ │Name   Proc  Unproc  Pct ││ │     /           \          │   │
│ │ │Jane    45     5    90% ││ │    │  On Track  │          │   │
│ │ │John    38    12    76% ││ │    │    85%     │          │   │
│ │ │...                     ││ │     \           /          │   │
│ │ └─────────────────────────┘│ │      └─────────┘           │   │
│ └────────────────────────────┘ │ At-Risk: 8  Breached: 12   │   │
│                                └────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Implementation Changes

**File:** `frontend/src/pages/Dashboard.tsx`

1. Remove `featuresApi` import and query
2. Remove "Features by Product Area" panel
3. Remove "Notes by Type" panel
4. Add "Avg Response Time" stat card
5. Add "Notes by Owner" table (left panel)
6. Add "SLA Status" donut chart (right panel)

**New API calls needed:**
- `GET /reports/notes-insights?days=30` - for owner table
- `GET /reports/sla` - for SLA donut data

### 3.3 SLA Donut Chart Component

```tsx
function SLADonut({ data }: { data: { breached: number; at_risk: number; on_track: number } }) {
  const total = data.breached + data.at_risk + data.on_track;
  const onTrackPct = Math.round((data.on_track / total) * 100);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-900 mb-4">SLA Status</h3>
      {/* Recharts PieChart with 3 segments */}
      <div className="flex justify-center gap-4 mt-4 text-sm">
        <span className="text-green-600">On Track: {data.on_track}</span>
        <span className="text-yellow-600">At Risk: {data.at_risk}</span>
        <span className="text-red-600">Breached: {data.breached}</span>
      </div>
    </div>
  );
}
```

---

## Phase 4: Insights Page Enhancement

### 4.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Notes Insights                           [Last 90 days ▼]      │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│ │ Created  │ │Processed │ │Unprocessed│ │  Avg Response Time  │ │
│ │   523    │ │   489    │ │    34    │ │      2.1 days       │ │
│ │   ↑12%   │ │   ↑15%   │ │   ↓23%   │ │       ↓8%          │ │
│ └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────┐ ┌────────────────────────────┐   │
│ │      Notes Trend           │ │  Response Time Distribution│   │
│ │         ___                │ │    ████                    │   │
│ │       _/   \__             │ │    ████ ███                │   │
│ │      /        \___         │ │    ████ ███ ██             │   │
│ │   __/              \       │ │    ████ ███ ██ █           │   │
│ │  Created  ── Processed     │ │    <1d  1-3  3-5  5+       │   │
│ └────────────────────────────┘ └────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  Owner Performance                                              │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ Name      Assigned  Processed  Unproc  Progress  AvgResp  SLA│ │
│ │ Jane Doe     45        40        5      89%      2.3d     1 │ │
│ │ John Smith   38        26       12      68%      3.1d     4 │ │
│ └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Implementation Changes

**File:** `frontend/src/pages/NotesInsightsPage.tsx`

1. Add "Avg Response Time" stat card (4th card)
2. Replace "Notes by source" chart with "Notes Trend" line chart
3. Add "Response Time Distribution" histogram
4. Enhance owner table with new columns:
   - `avg_response_time` (days)
   - `sla_breached` (count)
5. Rename "makers" to "owners" in UI and API

### 4.3 Notes Trend Chart

**New API needed:** `GET /reports/notes-trend?days=90`
```json
{
  "data": [
    {"week": "2025-W01", "created": 45, "processed": 42},
    {"week": "2025-W02", "created": 52, "processed": 48},
    ...
  ]
}
```

```tsx
function NotesTrendChart({ data }: { data: Array<{week: string; created: number; processed: number}> }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="week" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="created" stroke="#3B82F6" name="Created" />
        <Line type="monotone" dataKey="processed" stroke="#10B981" name="Processed" />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### 4.4 Response Time Distribution Histogram

```tsx
function ResponseTimeHistogram({ data }: { data: Array<{bucket: string; count: number}> }) {
  const COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#EF4444'];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="bucket" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((_, index) => (
            <Cell key={index} fill={COLORS[index]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

---

## Phase 5: SLA Page Enhancement

### 5.1 Add Owner Breakdown Section

**File:** `frontend/src/pages/SLAPage.tsx`

Add a new section below the note tables:

```tsx
{/* SLA by Owner */}
<div className="mt-8">
  <h2 className="text-lg font-semibold text-gray-900 mb-4">SLA by Owner</h2>
  <div className="bg-white rounded-lg shadow overflow-hidden">
    <table className="min-w-full divide-y divide-gray-200">
      <thead className="bg-gray-50">
        <tr>
          <th>Owner</th>
          <th>Breached</th>
          <th>At Risk</th>
          <th>On Track</th>
          <th>Compliance Rate</th>
        </tr>
      </thead>
      <tbody>
        {slaByOwner.map(owner => (
          <tr key={owner.id} className="hover:bg-gray-50 cursor-pointer"
              onClick={() => navigate(`/notes?owner_id=${owner.id}&state=unprocessed`)}>
            <td>{owner.name}</td>
            <td className="text-red-600">{owner.breached}</td>
            <td className="text-yellow-600">{owner.at_risk}</td>
            <td className="text-green-600">{owner.on_track}</td>
            <td>{owner.compliance_rate}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
</div>
```

### 5.2 Backend Enhancement

**Update `GET /reports/sla` to include:**
```json
{
  "summary": {...},
  "breached_notes": [...],
  "at_risk_notes": [...],
  "by_owner": [
    {
      "id": 1,
      "name": "Jane Doe",
      "breached": 2,
      "at_risk": 3,
      "on_track": 10,
      "compliance_rate": 87.5
    }
  ]
}
```

---

## Phase 6: Notes List Page Updates

### 6.1 Minor Updates

**File:** `frontend/src/pages/NotesListPage.tsx`

No major changes needed - filtering and grouping already works well.

**File:** `frontend/src/components/NotesTable.tsx`

1. Add "Response Time" column (for processed notes)
2. Add "Tags" display as chips
3. Update to show `source_origin` instead of `source` if displayed

### 6.2 Response Time Column

```tsx
<td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
  {note.response_time_days !== null
    ? `${note.response_time_days} days`
    : note.state === 'processed' ? 'N/A' : '-'}
</td>
```

---

## Phase 7: Frontend API Updates

### 7.1 Update `frontend/src/api/notes.ts`

Update `Note` interface:
```typescript
interface Note {
  id: number;
  pb_id: string;
  title: string;
  content: string;
  state: string;
  source_origin: string;  // renamed from source
  display_url: string;
  external_display_url: string;
  tags: string[];  // NEW
  followers_count: number;  // NEW
  created_at: string;
  updated_at: string;
  processed_at: string | null;
  response_time_days: number | null;  // NEW
  owner: { id: number; name: string; email: string } | null;
  creator: { id: number; name: string; email: string } | null;  // renamed from created_by
  company: { id: number; name: string } | null;
}
```

### 7.2 Update `frontend/src/api/reports.ts`

Add new types and endpoints:
```typescript
interface ResponseTimeStats {
  average_days: number;
  median_days: number;
  distribution: Array<{ bucket: string; count: number }>;
  by_owner: Array<{ id: number; name: string; avg_response_time: number; count: number }>;
  trend: Array<{ week: string; avg_response_time: number }>;
}

interface NotesTrend {
  data: Array<{ week: string; created: number; processed: number }>;
}

export const reportsApi = {
  // ... existing methods

  getResponseTime: (days: number = 90) =>
    client.get<ResponseTimeStats>(`/reports/response-time?days=${days}`),

  getNotesTrend: (days: number = 90) =>
    client.get<NotesTrend>(`/reports/notes-trend?days=${days}`),
};
```

---

## Implementation Order

1. **Backend API fixes** (Phase 1) - Required before frontend works
2. **Remove deprecated pages** (Phase 2) - Quick cleanup
3. **Dashboard redesign** (Phase 3) - High visibility win
4. **Insights enhancement** (Phase 4) - Core analytics value
5. **SLA enhancement** (Phase 5) - Adds owner accountability
6. **Notes page updates** (Phase 6) - Polish
7. **API type updates** (Phase 7) - Can be done alongside each phase

---

## Files to Modify

### Backend
- `backend/app/api/notes.py` - Major update
- `backend/app/api/reports.py` - Major update + new endpoints

### Frontend - Delete
- `frontend/src/pages/FeaturesListPage.tsx`
- `frontend/src/pages/FeatureDetailPage.tsx`
- `frontend/src/pages/WorkloadPage.tsx`
- `frontend/src/components/FeaturesTable.tsx`
- `frontend/src/api/features.ts`

### Frontend - Modify
- `frontend/src/App.tsx` - Remove routes and nav
- `frontend/src/pages/Dashboard.tsx` - Redesign
- `frontend/src/pages/NotesInsightsPage.tsx` - Major update
- `frontend/src/pages/SLAPage.tsx` - Add owner breakdown
- `frontend/src/pages/NotesListPage.tsx` - Minor updates
- `frontend/src/components/NotesTable.tsx` - Add columns
- `frontend/src/api/notes.ts` - Update types
- `frontend/src/api/reports.ts` - Add endpoints

---

## Success Criteria

1. All pages load without errors
2. Dashboard shows 4 metric cards + owner table + SLA donut
3. Insights shows trend chart, response time histogram, enhanced owner table
4. SLA page shows owner breakdown with compliance rates
5. Notes list shows response time column for processed notes
6. No references to old model (User, Note.type, Note.source, customer_id)
