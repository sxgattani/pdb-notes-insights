import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { notesApi } from '../api/notes';
import { featuresApi } from '../api/features';
import { StatCard } from '../components/StatCard';

export function Dashboard() {
  const navigate = useNavigate();

  const { data: notesStats, isLoading: notesLoading } = useQuery({
    queryKey: ['notes', 'stats'],
    queryFn: () => notesApi.getStats().then(r => r.data),
  });

  const { data: featuresStats, isLoading: featuresLoading } = useQuery({
    queryKey: ['features', 'stats'],
    queryFn: () => featuresApi.getStats().then(r => r.data),
  });

  if (notesLoading || featuresLoading) {
    return <div className="p-8">Loading...</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Dashboard</h1>

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
          title="Total Features"
          value={featuresStats?.total || 0}
          onClick={() => navigate('/features')}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Notes by Type</h2>
          <div className="space-y-2">
            {Object.entries(notesStats?.by_type || {}).map(([type, count]) => (
              <div key={type} className="flex justify-between">
                <span className="text-gray-600">{type}</span>
                <span className="font-medium">{count as number}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Features by Product Area</h2>
          <div className="space-y-2">
            {Object.entries(featuresStats?.by_product_area || {}).map(([area, count]) => (
              <div key={area} className="flex justify-between">
                <span className="text-gray-600">{area}</span>
                <span className="font-medium">{count as number}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
