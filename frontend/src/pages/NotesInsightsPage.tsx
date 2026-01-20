import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, Cell
} from 'recharts';
import { reportsApi } from '../api/reports';
import type { FloatStatWithChange, StatWithChange } from '../api/reports';

function formatNumber(num: number): string {
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
  }
  return num.toString();
}

function StatCard({
  title,
  stat,
  periodDays,
  suffix,
  onClick,
}: {
  title: string;
  stat: StatWithChange | FloatStatWithChange;
  periodDays: number;
  suffix?: string;
  onClick?: () => void;
}) {
  const hasChange = stat.change !== null;
  const isPositive = hasChange && stat.change! > 0;
  const isNegative = hasChange && stat.change! < 0;

  // For response time, lower is better so invert the colors
  const isResponseTime = title.toLowerCase().includes('response');
  const positiveColor = isResponseTime ? 'text-red-600' : 'text-red-600';
  const negativeColor = isResponseTime ? 'text-green-600' : 'text-green-600';

  return (
    <div
      className={`bg-white rounded-lg shadow p-6 ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}`}
      onClick={onClick}
    >
      <h3 className="text-sm font-medium text-gray-600">{title}</h3>
      <div className="mt-2 flex items-baseline space-x-3">
        <span className="text-3xl font-bold text-gray-900">
          {stat.value !== null ? (typeof stat.value === 'number' && stat.value % 1 !== 0 ? stat.value.toFixed(1) : formatNumber(stat.value as number)) : '-'}
        </span>
        {suffix && <span className="text-lg text-gray-500">{suffix}</span>}
        {hasChange && (
          <span className={`text-sm font-medium ${isPositive ? positiveColor : isNegative ? negativeColor : 'text-gray-500'}`}>
            {isPositive ? '↑' : isNegative ? '↓' : ''}{Math.abs(stat.change!)}%
          </span>
        )}
      </div>
      <p className="mt-1 text-xs text-gray-500">{periodDays === 1 ? 'Last 24 hours' : `Last ${periodDays} days`}</p>
    </div>
  );
}

function NotesTrendChart({ data }: { data: Array<{ week: string; created: number; processed: number }> }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-900 mb-4">Notes Trend</h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="week"
              tick={{ fontSize: 11 }}
              tickFormatter={(value) => value.split('-')[1]}
            />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ borderRadius: '8px', border: '1px solid #E5E7EB' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="created"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Created"
            />
            <Line
              type="monotone"
              dataKey="processed"
              stroke="#10B981"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Processed"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ResponseTimeHistogram({ data }: { data: Array<{ bucket: string; count: number }> }) {
  const COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#EF4444'];

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-900 mb-4">Response Time Distribution</h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ borderRadius: '8px', border: '1px solid #E5E7EB' }}
              formatter={(value) => [value ?? 0, 'Notes']}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function OwnersTable({
  owners,
  onRowClick,
}: {
  owners: Array<{
    id: number;
    name: string;
    assigned: number;
    processed: number;
    unprocessed: number;
    progress: number;
    avg_response_time: number | null;
    sla_breached: number;
  }>;
  onRowClick: (ownerId: number) => void;
}) {
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b">
        <h3 className="text-sm font-medium text-gray-900">Owner Performance</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Owner
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Assigned
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Processed
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Unprocessed
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Progress
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Avg Response
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                SLA Breached
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {owners.map((owner) => (
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
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                  {owner.assigned}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                  {owner.processed}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                  {owner.unprocessed}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <span className={`font-medium ${owner.progress >= 80 ? 'text-green-600' : owner.progress >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                    {owner.progress}%
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  {owner.avg_response_time !== null ? (
                    <span className={`font-medium ${owner.avg_response_time <= 3 ? 'text-green-600' : owner.avg_response_time <= 5 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {owner.avg_response_time.toFixed(1)}d
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  {owner.sla_breached > 0 ? (
                    <span className="text-red-600 font-medium">{owner.sla_breached}</span>
                  ) : (
                    <span className="text-green-600">0</span>
                  )}
                </td>
              </tr>
            ))}
            {owners.length === 0 && (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                  No data available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

type PeriodType = 'preset' | 'custom';

function formatDateForInput(date: Date): string {
  return date.toISOString().split('T')[0];
}

export function NotesInsightsPage() {
  const navigate = useNavigate();

  // Period selection state
  const [periodType, setPeriodType] = useState<PeriodType>('preset');
  const [presetDays, setPresetDays] = useState(90);
  const [customStart, setCustomStart] = useState(() => formatDateForInput(new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)));
  const [customEnd, setCustomEnd] = useState(() => formatDateForInput(new Date()));

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

  const { data: insightsData, isLoading: insightsLoading } = useQuery({
    queryKey: ['reports', 'notes-insights', effectiveDays],
    queryFn: () => reportsApi.getNotesInsights(effectiveDays).then((r) => r.data),
  });

  const { data: trendData, isLoading: trendLoading } = useQuery({
    queryKey: ['reports', 'notes-trend', effectiveDays],
    queryFn: () => reportsApi.getNotesTrend(effectiveDays).then((r) => r.data),
  });

  const { data: responseTimeData, isLoading: responseTimeLoading } = useQuery({
    queryKey: ['reports', 'response-time', effectiveDays],
    queryFn: () => reportsApi.getResponseTime(effectiveDays).then((r) => r.data),
  });

  // Date filter query string for navigation
  const dateFilterParams = useMemo(() => {
    if (periodType === 'custom') {
      return `created_after=${customStart}&created_before=${customEnd}`;
    }
    const endDate = new Date();
    const startDate = new Date(Date.now() - presetDays * 24 * 60 * 60 * 1000);
    return `created_after=${formatDateForInput(startDate)}&created_before=${formatDateForInput(endDate)}`;
  }, [periodType, presetDays, customStart, customEnd]);

  const isLoading = insightsLoading || trendLoading || responseTimeLoading;

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-48"></div>
          <div className="grid grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-6">
            <div className="h-80 bg-gray-200 rounded"></div>
            <div className="h-80 bg-gray-200 rounded"></div>
          </div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  const handleOwnerClick = (ownerId: number) => {
    navigate(`/notes?owner_id=${ownerId}&${dateFilterParams}`);
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Notes Insights</h1>
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

      {insightsData && (
        <div className="space-y-6">
          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
            <StatCard
              title="Created Notes"
              stat={insightsData.summary.created}
              periodDays={effectiveDays}
              onClick={() => navigate(`/notes?${dateFilterParams}`)}
            />
            <StatCard
              title="Processed Notes"
              stat={insightsData.summary.processed}
              periodDays={effectiveDays}
              onClick={() => navigate(`/notes?state=processed&${dateFilterParams}`)}
            />
            <StatCard
              title="Unprocessed Notes"
              stat={insightsData.summary.unprocessed}
              periodDays={effectiveDays}
              onClick={() => navigate(`/notes?state=unprocessed&${dateFilterParams}`)}
            />
            <StatCard
              title="Unassigned Notes"
              stat={insightsData.summary.unassigned}
              periodDays={effectiveDays}
              onClick={() => navigate(`/notes?unassigned=true&${dateFilterParams}`)}
            />
            <StatCard
              title="Avg Response Time"
              stat={insightsData.summary.avg_response_time}
              periodDays={effectiveDays}
              suffix="days"
              onClick={() => navigate(`/notes?state=processed&${dateFilterParams}`)}
            />
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {trendData && <NotesTrendChart data={trendData.data} />}
            {responseTimeData && <ResponseTimeHistogram data={responseTimeData.distribution} />}
          </div>

          {/* Owners Table */}
          <OwnersTable owners={insightsData.by_owner} onRowClick={handleOwnerClick} />
        </div>
      )}
    </div>
  );
}
