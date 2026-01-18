import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { featuresApi } from '../api/features';

export function FeatureDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: feature, isLoading, isError } = useQuery({
    queryKey: ['features', 'detail', id],
    queryFn: () => featuresApi.get(Number(id)).then((r) => r.data),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Loading feature...
        </div>
      </div>
    );
  }

  if (isError || !feature) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-red-600 mb-4">Feature not found</p>
          <button
            onClick={() => navigate('/features')}
            className="text-blue-600 hover:underline"
          >
            Back to features
          </button>
        </div>
      </div>
    );
  }

  const committedColors = feature.committed
    ? 'bg-green-100 text-green-800'
    : 'bg-gray-100 text-gray-600';

  const riskColors: Record<string, string> = {
    high: 'bg-red-100 text-red-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-green-100 text-green-800',
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/features')}
          className="text-sm text-gray-500 hover:text-gray-700 mb-2 flex items-center"
        >
          ← Back to features
        </button>
        <div className="flex items-start justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            {feature.name || '(No name)'}
          </h1>
          <div className="flex space-x-2">
            <span className={`px-3 py-1 rounded-full text-sm ${committedColors}`}>
              {feature.committed ? 'Committed' : 'Not Committed'}
            </span>
            {feature.risk && (
              <span className={`px-3 py-1 rounded-full text-sm ${riskColors[feature.risk.toLowerCase()] || 'bg-gray-100 text-gray-600'}`}>
                {feature.risk}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Product Area</dt>
            <dd className="mt-1 text-sm text-gray-900">{feature.product_area || '-'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Status</dt>
            <dd className="mt-1 text-sm text-gray-900">{feature.status || '-'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Type</dt>
            <dd className="mt-1 text-sm text-gray-900">{feature.type || '-'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Stack Rank</dt>
            <dd className="mt-1 text-sm text-gray-900">{feature.product_area_stack_rank ?? '-'}</dd>
          </div>
        </div>
      </div>

      {/* Description */}
      {feature.description && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Description</h2>
            <div className="prose max-w-none text-gray-700 whitespace-pre-wrap">
              {feature.description}
            </div>
          </div>
        </div>
      )}

      {/* Linked Notes */}
      {feature.notes && feature.notes.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Linked Notes ({feature.notes.length})
            </h2>
            <div className="space-y-2">
              {feature.notes.map((note) => (
                <Link
                  key={note.id}
                  to={`/notes/${note.id}`}
                  className="block p-3 border rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-medium text-gray-900">{note.title || '(No title)'}</span>
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        note.state === 'processed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {note.state}
                      </span>
                      {note.created_at && (
                        <span className="text-sm text-gray-500">
                          {new Date(note.created_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
