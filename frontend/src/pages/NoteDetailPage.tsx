import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { notesApi } from '../api/notes';

export function NoteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: note, isLoading, isError } = useQuery({
    queryKey: ['notes', 'detail', id],
    queryFn: () => notesApi.get(Number(id)).then((r) => r.data),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Loading note...
        </div>
      </div>
    );
  }

  if (isError || !note) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-red-600 mb-4">Note not found</p>
          <button
            onClick={() => navigate('/notes')}
            className="text-blue-600 hover:underline"
          >
            Back to notes
          </button>
        </div>
      </div>
    );
  }

  const stateColors = note.state === 'processed'
    ? 'bg-green-100 text-green-800'
    : 'bg-yellow-100 text-yellow-800';

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/notes')}
          className="text-sm text-gray-500 hover:text-gray-700 mb-2 flex items-center"
        >
          ← Back to notes
        </button>
        <div className="flex items-start justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            {note.title || '(No title)'}
          </h1>
          <span className={`px-3 py-1 rounded-full text-sm ${stateColors}`}>
            {note.state}
          </span>
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Type</dt>
            <dd className="mt-1 text-sm text-gray-900">{note.type || '-'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Source</dt>
            <dd className="mt-1 text-sm text-gray-900">{note.source || '-'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Created</dt>
            <dd className="mt-1 text-sm text-gray-900">
              {note.created_at ? new Date(note.created_at).toLocaleString() : '-'}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Processed</dt>
            <dd className="mt-1 text-sm text-gray-900">
              {note.processed_at ? new Date(note.processed_at).toLocaleString() : '-'}
            </dd>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Content</h2>
          <div className="prose max-w-none text-gray-700 whitespace-pre-wrap">
            {note.content || '(No content)'}
          </div>
        </div>
      </div>

      {/* Linked Features */}
      {note.features && note.features.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Linked Features ({note.features.length})
            </h2>
            <div className="space-y-2">
              {note.features.map((feature) => (
                <Link
                  key={feature.id}
                  to={`/features/${feature.id}`}
                  className="block p-3 border rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-medium text-gray-900">{feature.name}</span>
                    {feature.product_area && (
                      <span className="text-sm text-gray-500">{feature.product_area}</span>
                    )}
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
