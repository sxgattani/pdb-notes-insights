import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { reportsApi } from '../api/reports';
import type { SLANote, SLAByOwner } from '../api/reports';

type PeriodType = 'preset' | 'custom';

const STORAGE_KEY = 'sla-period';

function getComplianceColor(rate: number): string {
  if (rate >= 90) return 'text-green-600';
  if (rate >= 75) return 'text-yellow-600';
  return 'text-red-600';
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString();
}

function formatDateForInput(date: Date): string {
  return date.toISOString().split('T')[0];
}

// Sort indicator component
function SortIndicator({ active, direction }: { active: boolean; direction: 'asc' | 'desc' }) {
  if (!active) {
    return (
      <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
      </svg>
    );
  }
  if (direction === 'asc') {
    return (
      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    );
  }
  return (
    <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

// SLA by Owner table with sorting
type OwnerSortField = 'name' | 'breached' | 'at_risk' | 'on_track' | 'compliance_rate';

function SLAByOwnerTable({
  owners,
  onRowClick,
}: {
  owners: SLAByOwner[];
  onRowClick: (ownerId: number) => void;
}) {
  const [sortField, setSortField] = useState<OwnerSortField>('breached');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const handleSort = (field: OwnerSortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const sortedOwners = useMemo(() => {
    return [...owners].sort((a, b) => {
      let aVal: number | string = sortField === 'name' ? a.name.toLowerCase() : a[sortField];
      let bVal: number | string = sortField === 'name' ? b.name.toLowerCase() : b[sortField];

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [owners, sortField, sortOrder]);

  const columns: Array<{ field: OwnerSortField; label: string; align: 'left' | 'right' }> = [
    { field: 'name', label: 'Owner', align: 'left' },
    { field: 'breached', label: 'Breached', align: 'right' },
    { field: 'at_risk', label: 'At Risk', align: 'right' },
    { field: 'on_track', label: 'On Track', align: 'right' },
    { field: 'compliance_rate', label: 'Compliance', align: 'right' },
  ];

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th
                key={col.field}
                onClick={() => handleSort(col.field)}
                className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 select-none ${
                  col.align === 'left' ? 'text-left' : 'text-right'
                }`}
              >
                <div className={`flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : ''}`}>
                  {col.label}
                  <SortIndicator active={sortField === col.field} direction={sortOrder} />
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedOwners.map((owner) => (
            <tr
              key={owner.id}
              onClick={() => onRowClick(owner.id)}
              className="hover:bg-gray-50 cursor-pointer"
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-sm font-medium mr-3">
                    {owner.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                  </div>
                  <span className="text-sm font-medium text-gray-900">{owner.name}</span>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                {owner.breached > 0 ? (
                  <span className="text-red-600 font-medium">{owner.breached}</span>
                ) : (
                  <span className="text-gray-400">0</span>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                {owner.at_risk > 0 ? (
                  <span className="text-yellow-600 font-medium">{owner.at_risk}</span>
                ) : (
                  <span className="text-gray-400">0</span>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                <span className="text-green-600">{owner.on_track}</span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                <span className={`font-medium ${getComplianceColor(owner.compliance_rate)}`}>
                  {owner.compliance_rate.toFixed(1)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {owners.length === 0 && (
        <div className="p-8 text-center text-gray-500">
          No owner data available
        </div>
      )}
    </div>
  );
}

// Notes table with sorting (for breached and at-risk)
type NoteSortField = 'title' | 'owner_name' | 'company_name' | 'days_old' | 'created_at';

function SLANotesTable({
  notes,
  type,
  onRowClick,
}: {
  notes: SLANote[];
  type: 'breached' | 'at-risk';
  onRowClick: (noteId: number) => void;
}) {
  const [sortField, setSortField] = useState<NoteSortField>('days_old');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const handleSort = (field: NoteSortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const sortedNotes = useMemo(() => {
    return [...notes].sort((a, b) => {
      let aVal: number | string;
      let bVal: number | string;

      switch (sortField) {
        case 'title':
          aVal = (a.title || '').toLowerCase();
          bVal = (b.title || '').toLowerCase();
          break;
        case 'owner_name':
          aVal = (a.owner_name || 'zzz').toLowerCase(); // Put nulls at end
          bVal = (b.owner_name || 'zzz').toLowerCase();
          break;
        case 'company_name':
          aVal = (a.company_name || 'zzz').toLowerCase();
          bVal = (b.company_name || 'zzz').toLowerCase();
          break;
        case 'created_at':
          aVal = new Date(a.created_at).getTime();
          bVal = new Date(b.created_at).getTime();
          break;
        default:
          aVal = a[sortField];
          bVal = b[sortField];
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [notes, sortField, sortOrder]);

  const isBreached = type === 'breached';
  const badgeColor = isBreached ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800';
  const rowHoverColor = isBreached ? 'hover:bg-red-50' : 'hover:bg-yellow-50';

  const columns: Array<{ field: NoteSortField; label: string; align: 'left' | 'right' }> = [
    { field: 'title', label: 'Title', align: 'left' },
    { field: 'owner_name', label: 'Owner', align: 'left' },
    { field: 'company_name', label: 'Company', align: 'left' },
    { field: 'days_old', label: 'Days Old', align: 'right' },
    { field: 'created_at', label: 'Created At', align: 'right' },
  ];

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th
                key={col.field}
                onClick={() => handleSort(col.field)}
                className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 select-none ${
                  col.align === 'left' ? 'text-left' : 'text-right'
                }`}
              >
                <div className={`flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : ''}`}>
                  {col.label}
                  <SortIndicator active={sortField === col.field} direction={sortOrder} />
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedNotes.map((note) => (
            <tr
              key={note.id}
              onClick={() => onRowClick(note.id)}
              className={`${rowHoverColor} cursor-pointer`}
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeColor} mr-3`}>
                    {isBreached ? 'Breached' : 'At Risk'}
                  </span>
                  <span className="font-medium text-gray-900">{note.title}</span>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {note.owner_name || <span className="text-gray-400">Unassigned</span>}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {note.company_name || <span className="text-gray-400">-</span>}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                <span className={isBreached ? 'text-red-600 font-medium' : 'text-yellow-600 font-medium'}>
                  {note.days_old} days
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                {formatDate(note.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {notes.length === 0 && (
        <div className="p-8 text-center text-gray-500">
          No {isBreached ? 'breached' : 'at-risk'} notes
        </div>
      )}
    </div>
  );
}

function loadStoredPeriod(): { periodType: PeriodType; presetDays: number; customStart: string; customEnd: string } {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {}
  return {
    periodType: 'preset',
    presetDays: 7,
    customStart: formatDateForInput(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)),
    customEnd: formatDateForInput(new Date()),
  };
}

export function SLAPage() {
  const navigate = useNavigate();

  // Period selection state - load from localStorage
  const initialPeriod = loadStoredPeriod();
  const [periodType, setPeriodType] = useState<PeriodType>(initialPeriod.periodType);
  const [presetDays, setPresetDays] = useState(initialPeriod.presetDays);
  const [customStart, setCustomStart] = useState(initialPeriod.customStart);
  const [customEnd, setCustomEnd] = useState(initialPeriod.customEnd);

  // Save to localStorage when period changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ periodType, presetDays, customStart, customEnd }));
  }, [periodType, presetDays, customStart, customEnd]);

  // Calculate effective days for API call
  const effectiveDays = useMemo(() => {
    if (periodType === 'preset') {
      return presetDays;
    }
    const start = new Date(customStart);
    const end = new Date(customEnd);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }, [periodType, presetDays, customStart, customEnd]);

  // Period label for display
  const periodLabel = useMemo(() => {
    if (periodType === 'preset') {
      if (presetDays === 1) return 'Last 24 hours';
      return `Last ${presetDays} days`;
    }
    return `${customStart} to ${customEnd}`;
  }, [periodType, presetDays, customStart, customEnd]);

  const { data, isLoading } = useQuery({
    queryKey: ['reports', 'sla', effectiveDays],
    queryFn: () => reportsApi.getSLA(effectiveDays).then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Loading SLA data...
        </div>
      </div>
    );
  }

  const summary = data?.summary;
  const breachedNotes = data?.breached_notes || [];
  const atRiskNotes = data?.at_risk_notes || [];
  const byOwner = data?.by_owner || [];
  const slaDays = data?.sla_days || 5;

  const handleRowClick = (noteId: number) => {
    navigate(`/notes/${noteId}`);
  };

  const handleOwnerClick = (ownerId: number) => {
    navigate(`/notes?owner_id=${ownerId}&state=unprocessed`);
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">SLA Compliance</h1>
        <div className="flex items-center gap-4">
          {/* Period Selector */}
          <div className="flex items-center gap-2 bg-white border rounded-lg px-3 py-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeWidth={2} />
              <line x1="16" y1="2" x2="16" y2="6" strokeWidth={2} />
              <line x1="8" y1="2" x2="8" y2="6" strokeWidth={2} />
              <line x1="3" y1="10" x2="21" y2="10" strokeWidth={2} />
            </svg>
            <select
              value={periodType === 'preset' ? presetDays.toString() : 'custom'}
              onChange={(e) => {
                const val = e.target.value;
                if (val === 'custom') {
                  setPeriodType('custom');
                } else {
                  setPeriodType('preset');
                  setPresetDays(parseInt(val, 10));
                }
              }}
              className="border-0 bg-transparent text-sm focus:ring-0 pr-8"
            >
              <option value="1">Last 24 hours</option>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="60">Last 60 days</option>
              <option value="90">Last 90 days</option>
              <option value="180">Last 180 days</option>
              <option value="365">Last 365 days</option>
              <option value="custom">Custom range</option>
            </select>
          </div>

          {/* Custom Date Inputs */}
          {periodType === 'custom' && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="border rounded px-2 py-1 text-sm"
              />
              <span className="text-gray-500">to</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="border rounded px-2 py-1 text-sm"
              />
            </div>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <p className="text-sm text-gray-500 mb-4">{periodLabel}</p>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Compliance Rate</h3>
          <p className={`mt-2 text-3xl font-semibold ${getComplianceColor(summary?.sla_compliance_rate || 0)}`}>
            {(summary?.sla_compliance_rate || 0).toFixed(1)}%
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Breached Notes</h3>
          <p className="mt-2 text-3xl font-semibold text-red-600">{summary?.breached || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">At-Risk Notes</h3>
          <p className="mt-2 text-3xl font-semibold text-yellow-600">{summary?.at_risk || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">On-Track Notes</h3>
          <p className="mt-2 text-3xl font-semibold text-green-600">{summary?.on_track || 0}</p>
        </div>
      </div>

      {/* SLA by Owner */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          SLA by Owner
        </h2>
        <SLAByOwnerTable owners={byOwner} onRowClick={handleOwnerClick} />
      </div>

      {/* Breached Notes Table */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Breached Notes
          <span className="ml-2 text-sm font-normal text-gray-500">(past {slaDays}-day SLA)</span>
        </h2>
        <SLANotesTable notes={breachedNotes} type="breached" onRowClick={handleRowClick} />
      </div>

      {/* At-Risk Notes Table */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          At-Risk Notes
          <span className="ml-2 text-sm font-normal text-gray-500">(approaching deadline)</span>
        </h2>
        <SLANotesTable notes={atRiskNotes} type="at-risk" onRowClick={handleRowClick} />
      </div>
    </div>
  );
}
