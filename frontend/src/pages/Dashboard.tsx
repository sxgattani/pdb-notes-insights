import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { notesApi } from '../api/notes';
import { reportsApi } from '../api/reports';
import { syncApi } from '../api/sync';
import { StatCard } from '../components/StatCard';

export function Dashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');

  const { data: notesStats, isLoading: notesLoading } = useQuery({
    queryKey: ['notes', 'stats'],
    queryFn: () => notesApi.getStats().then(r => r.data),
  });

  const { data: insightsData, isLoading: insightsLoading } = useQuery({
    queryKey: ['reports', 'notes-insights', 30],
    queryFn: () => reportsApi.getNotesInsights(30).then(r => r.data),
  });

  const { data: slaData, isLoading: slaLoading } = useQuery({
    queryKey: ['reports', 'sla'],
    queryFn: () => reportsApi.getSLA().then(r => r.data),
  });

  const { data: syncStatus } = useQuery({
    queryKey: ['sync', 'status'],
    queryFn: () => syncApi.getStatus().then(r => r.data),
    refetchInterval: syncing ? 3000 : false,
  });

  const handleSync = async () => {
    setSyncing(true);
    setSyncMessage('');
    try {
      await syncApi.trigger();
      setSyncMessage('Sync started! This may take a few minutes.');
      const checkStatus = setInterval(async () => {
        const status = await syncApi.getStatus();
        if (status.data.status === 'idle') {
          clearInterval(checkStatus);
          setSyncing(false);
          setSyncMessage('Sync completed!');
          queryClient.invalidateQueries();
          setTimeout(() => setSyncMessage(''), 5000);
        }
      }, 3000);
    } catch (error) {
      setSyncing(false);
      setSyncMessage('Sync failed. Check your API token.');
    }
  };

  if (notesLoading || insightsLoading || slaLoading) {
    return <div className="p-8">Loading...</div>;
  }

  const isSyncing = syncing || syncStatus?.status === 'running';

  // SLA donut data
  const slaChartData = slaData ? [
    { name: 'On Track', value: slaData.summary.on_track, color: '#10B981' },
    { name: 'At Risk', value: slaData.summary.at_risk, color: '#F59E0B' },
    { name: 'Breached', value: slaData.summary.breached, color: '#EF4444' },
  ].filter(d => d.value > 0) : [];

  const totalSla = slaChartData.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className="flex items-center gap-4">
          {syncMessage && (
            <span className={`text-sm ${syncMessage.includes('failed') ? 'text-red-600' : 'text-green-600'}`}>
              {syncMessage}
            </span>
          )}
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSyncing && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            )}
            {isSyncing ? 'Syncing...' : 'Sync from ProductBoard'}
          </button>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Notes"
          value={notesStats?.total || 0}
          onClick={() => navigate('/notes')}
        />
        <StatCard
          title="Processed"
          value={notesStats?.processed || 0}
          subtitle={`${Math.round((notesStats?.processed || 0) / (notesStats?.total || 1) * 100)}%`}
          onClick={() => navigate('/notes?state=processed')}
        />
        <StatCard
          title="Unprocessed"
          value={notesStats?.unprocessed || 0}
          onClick={() => navigate('/notes?state=unprocessed')}
        />
        <StatCard
          title="Avg Response Time"
          value={notesStats?.avg_response_time_days !== null ? `${notesStats?.avg_response_time_days}` : '-'}
          subtitle="days"
          onClick={() => navigate('/insights')}
        />
      </div>

      {/* Two Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Notes by Owner Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">Notes by Owner</h2>
            <p className="text-sm text-gray-500">Last 30 days</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Assigned</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Processed</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Progress</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {(insightsData?.by_owner || []).slice(0, 8).map((owner) => (
                  <tr
                    key={owner.id}
                    onClick={() => navigate(`/notes?owner_id=${owner.id}`)}
                    className="hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-6 py-3 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-sm font-medium mr-3">
                          {owner.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                        </div>
                        <span className="text-sm font-medium text-gray-900">{owner.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-right text-gray-500">
                      {owner.assigned}
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-right text-green-600">
                      {owner.processed}
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-right">
                      <span className={`font-medium ${owner.progress >= 80 ? 'text-green-600' : owner.progress >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {owner.progress}%
                      </span>
                    </td>
                  </tr>
                ))}
                {(!insightsData?.by_owner || insightsData.by_owner.length === 0) && (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                      No owner data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {(insightsData?.by_owner?.length || 0) > 8 && (
            <div className="px-6 py-3 border-t bg-gray-50">
              <button
                onClick={() => navigate('/insights')}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                View all {insightsData?.by_owner.length} owners →
              </button>
            </div>
          )}
        </div>

        {/* SLA Status Donut */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">SLA Status</h2>
          <p className="text-sm text-gray-500 mb-4">Unprocessed notes compliance</p>

          {totalSla > 0 ? (
            <>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={slaChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {slaChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value, name) => [value ?? 0, name ?? '']}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-6 mt-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <span className="text-sm text-gray-600">On Track: {slaData?.summary.on_track || 0}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                  <span className="text-sm text-gray-600">At Risk: {slaData?.summary.at_risk || 0}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <span className="text-sm text-gray-600">Breached: {slaData?.summary.breached || 0}</span>
                </div>
              </div>
              <div className="text-center mt-4">
                <span className={`text-2xl font-bold ${
                  (slaData?.summary.sla_compliance_rate || 0) >= 90 ? 'text-green-600' :
                  (slaData?.summary.sla_compliance_rate || 0) >= 75 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {slaData?.summary.sla_compliance_rate?.toFixed(1)}%
                </span>
                <p className="text-sm text-gray-500">Compliance Rate</p>
              </div>
            </>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              No unprocessed notes
            </div>
          )}

          <div className="mt-4 pt-4 border-t">
            <button
              onClick={() => navigate('/sla')}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              View full SLA report →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
