import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { reportsApi } from '../api/reports';

export function WorkloadPage() {
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['reports', 'workload'],
    queryFn: () => reportsApi.getWorkload().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Loading workload data...
        </div>
      </div>
    );
  }

  const workload = data?.data || [];
  const summary = data?.summary;

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">PM Workload</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Team Members</h3>
          <p className="mt-2 text-3xl font-semibold text-gray-900">{summary?.total_users || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Unprocessed Notes</h3>
          <p className="mt-2 text-3xl font-semibold text-yellow-600">{summary?.total_unprocessed || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Processed Notes</h3>
          <p className="mt-2 text-3xl font-semibold text-green-600">{summary?.total_processed || 0}</p>
        </div>
      </div>

      {/* Workload Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Unprocessed</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Processed</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Notes</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Features</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {workload.map((user) => (
              <tr
                key={user.user_id}
                onClick={() => navigate(`/notes?owner_id=${user.user_id}`)}
                className="hover:bg-gray-50 cursor-pointer"
              >
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                  {user.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.email || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <span className={user.unprocessed_notes > 0 ? 'text-yellow-600 font-medium' : 'text-gray-500'}>
                    {user.unprocessed_notes}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600">
                  {user.processed_notes}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                  {user.total_notes}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                  {user.total_features}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {workload.length === 0 && (
          <div className="p-8 text-center text-gray-500">No workload data available</div>
        )}
      </div>
    </div>
  );
}
