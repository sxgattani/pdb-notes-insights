import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { reportsApi, SLANote } from '../api/reports';

function getComplianceColor(rate: number): string {
  if (rate >= 90) return 'text-green-600';
  if (rate >= 75) return 'text-yellow-600';
  return 'text-red-600';
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString();
}

export function SLAPage() {
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['reports', 'sla'],
    queryFn: () => reportsApi.getSLA().then((r) => r.data),
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
  const slaDays = data?.sla_days || 5;

  // Sort by days_old descending (oldest first)
  const sortedBreachedNotes = [...breachedNotes].sort((a, b) => b.days_old - a.days_old);
  const sortedAtRiskNotes = [...atRiskNotes].sort((a, b) => b.days_old - a.days_old);

  const handleRowClick = (noteId: number) => {
    navigate(`/notes/${noteId}`);
  };

  const renderNotesTable = (notes: SLANote[], type: 'breached' | 'at-risk') => {
    const isBreached = type === 'breached';
    const badgeColor = isBreached ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800';
    const rowHoverColor = isBreached ? 'hover:bg-red-50' : 'hover:bg-yellow-50';

    return (
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Days Old</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Created At</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {notes.map((note) => (
              <tr
                key={note.id}
                onClick={() => handleRowClick(note.id)}
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
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">SLA Compliance</h1>

      {/* Summary Cards */}
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

      {/* Breached Notes Table */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Breached Notes
          <span className="ml-2 text-sm font-normal text-gray-500">(past {slaDays}-day SLA)</span>
        </h2>
        {renderNotesTable(sortedBreachedNotes, 'breached')}
      </div>

      {/* At-Risk Notes Table */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          At-Risk Notes
          <span className="ml-2 text-sm font-normal text-gray-500">(approaching deadline)</span>
        </h2>
        {renderNotesTable(sortedAtRiskNotes, 'at-risk')}
      </div>
    </div>
  );
}
