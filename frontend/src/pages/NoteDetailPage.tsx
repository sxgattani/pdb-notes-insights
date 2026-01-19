import { useParams, useNavigate } from 'react-router-dom';
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
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {note.title || '(No title)'}
            </h1>
            {note.tags && note.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {note.tags.map((tag, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-600"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-sm ${stateColors}`}>
              {note.state}
            </span>
            {note.display_url && (
              <a
                href={note.display_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Open in ProductBoard →
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Owner</dt>
            <dd className="mt-1 text-sm text-gray-900">
              {note.owner?.name || note.owner?.email || '-'}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Creator</dt>
            <dd className="mt-1 text-sm text-gray-900">
              {note.creator?.name || note.creator?.email || '-'}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Company</dt>
            <dd className="mt-1 text-sm text-gray-900">
              {note.company?.name || '-'}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Source</dt>
            <dd className="mt-1 text-sm text-gray-900">{note.source_origin || '-'}</dd>
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
          <div>
            <dt className="text-sm font-medium text-gray-500">Response Time</dt>
            <dd className="mt-1 text-sm">
              {note.response_time_days !== null ? (
                <span className={`font-medium ${
                  note.response_time_days <= 3 ? 'text-green-600' :
                  note.response_time_days <= 5 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {note.response_time_days.toFixed(1)} days
                </span>
              ) : (
                <span className="text-gray-500">
                  {note.state === 'unprocessed' ? 'Pending' : '-'}
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Followers</dt>
            <dd className="mt-1 text-sm text-gray-900">{note.followers_count || 0}</dd>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Content</h2>
          {note.content ? (
            <div
              className="prose max-w-none text-gray-700"
              dangerouslySetInnerHTML={{ __html: note.content }}
            />
          ) : (
            <p className="text-gray-500">(No content)</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Linked Features */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Linked Features ({note.features?.length || 0})
            </h2>
            {note.features && note.features.length > 0 ? (
              <div className="space-y-2">
                {note.features.map((feature) => (
                  <a
                    key={feature.id}
                    href={feature.display_url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-medium text-gray-900">
                        {feature.name || feature.pb_id}
                      </span>
                      {feature.importance && (
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                          {feature.importance}
                        </span>
                      )}
                    </div>
                  </a>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No linked features</p>
            )}
          </div>
        </div>

        {/* Comments */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Comments ({note.comments?.length || 0})
            </h2>
            {note.comments && note.comments.length > 0 ? (
              <div className="space-y-4">
                {note.comments.map((comment) => (
                  <div key={comment.id} className="border-b pb-4 last:border-b-0 last:pb-0">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-gray-900">
                        {comment.member?.name || comment.member?.email || 'Unknown'}
                      </span>
                      <span className="text-xs text-gray-500">
                        {comment.timestamp ? new Date(comment.timestamp).toLocaleString() : ''}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700">{comment.content}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No comments</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
