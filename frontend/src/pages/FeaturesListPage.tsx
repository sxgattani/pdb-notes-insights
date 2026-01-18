import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { featuresApi } from '../api/features';
import type { FeaturesParams } from '../api/features';
import { FeaturesTable } from '../components/FeaturesTable';
import { Pagination } from '../components/Pagination';

export function FeaturesListPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse URL params
  const page = parseInt(searchParams.get('page') || '1', 10);
  const product_area = searchParams.get('product_area') || '';
  const committed = searchParams.get('committed');
  const sort = searchParams.get('sort') || 'created_at';
  const order = (searchParams.get('order') || 'desc') as 'asc' | 'desc';

  const params: FeaturesParams = {
    page,
    limit: 20,
    sort,
    order,
    ...(product_area && { product_area }),
    ...(committed !== null && committed !== '' && { committed: committed === 'true' }),
  };

  const { data, isLoading } = useQuery({
    queryKey: ['features', 'list', params],
    queryFn: () => featuresApi.list(params).then((r) => r.data),
  });

  // Get unique product areas for filter dropdown
  const { data: stats } = useQuery({
    queryKey: ['features', 'stats'],
    queryFn: () => featuresApi.getStats().then((r) => r.data),
  });

  const productAreas = Object.keys(stats?.by_product_area || {});

  const updateParams = (updates: Record<string, string | undefined>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) {
        newParams.set(key, value);
      } else {
        newParams.delete(key);
      }
    });
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
        <h1 className="text-2xl font-bold text-gray-900">Features</h1>
        <div className="flex items-center space-x-4">
          {/* Product Area Filter */}
          <select
            value={product_area}
            onChange={(e) => updateParams({ product_area: e.target.value || undefined })}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">All Product Areas</option>
            {productAreas.map((area) => (
              <option key={area} value={area}>{area}</option>
            ))}
          </select>

          {/* Committed Filter */}
          <select
            value={committed ?? ''}
            onChange={(e) => updateParams({ committed: e.target.value || undefined })}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">All</option>
            <option value="true">Committed</option>
            <option value="false">Not Committed</option>
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
            <option value="name-asc">Name A-Z</option>
            <option value="name-desc">Name Z-A</option>
          </select>
        </div>
      </div>

      <FeaturesTable features={data?.data || []} isLoading={isLoading} />

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
