import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { notesApi } from '../api/notes';
import type { NotesParams } from '../api/notes';
import { NotesTable } from '../components/NotesTable';
import { Pagination } from '../components/Pagination';

export function NotesListPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse URL params
  const page = parseInt(searchParams.get('page') || '1', 10);
  const state = searchParams.get('state') || '';
  const sort = searchParams.get('sort') || 'created_at';
  const order = (searchParams.get('order') || 'desc') as 'asc' | 'desc';

  const params: NotesParams = {
    page,
    limit: 20,
    sort,
    order,
    ...(state && { state }),
  };

  const { data, isLoading } = useQuery({
    queryKey: ['notes', 'list', params],
    queryFn: () => notesApi.list(params).then((r) => r.data),
  });

  const updateParams = (updates: Record<string, string | undefined>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) {
        newParams.set(key, value);
      } else {
        newParams.delete(key);
      }
    });
    // Reset to page 1 when filters change
    if (!updates.page) {
      newParams.set('page', '1');
    }
    setSearchParams(newParams);
  };

  const handlePageChange = (newPage: number) => {
    updateParams({ page: String(newPage) });
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Notes</h1>
        <div className="flex items-center space-x-4">
          {/* State Filter */}
          <select
            value={state}
            onChange={(e) => updateParams({ state: e.target.value || undefined })}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">All States</option>
            <option value="unprocessed">Unprocessed</option>
            <option value="processed">Processed</option>
          </select>

          {/* Sort Order */}
          <select
            value={`${sort}-${order}`}
            onChange={(e) => {
              const [newSort, newOrder] = e.target.value.split('-');
              updateParams({ sort: newSort, order: newOrder });
            }}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="created_at-desc">Newest First</option>
            <option value="created_at-asc">Oldest First</option>
            <option value="title-asc">Title A-Z</option>
            <option value="title-desc">Title Z-A</option>
          </select>
        </div>
      </div>

      <NotesTable notes={data?.data || []} isLoading={isLoading} />

      {data && (
        <Pagination
          page={data.pagination.page}
          totalPages={data.pagination.pages}
          onPageChange={handlePageChange}
        />
      )}
    </div>
  );
}
