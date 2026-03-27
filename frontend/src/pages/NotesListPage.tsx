import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { notesApi } from '../api/notes';
import type { NotesParams } from '../api/notes';
import { NotesTable } from '../components/NotesTable';
import { Pagination } from '../components/Pagination';

const COLUMN_DEFINITIONS: { id: string; label: string }[] = [
  { id: 'title', label: 'Title' },
  { id: 'company', label: 'Company' },
  { id: 'owner', label: 'Owner' },
  { id: 'state', label: 'State' },
  { id: 'has_features', label: 'Linked Feature' },
  { id: 'response_time_days', label: 'Response Time' },
  { id: 'updated_at', label: 'Updated' },
  { id: 'created_at', label: 'Created' },
];

const DEFAULT_VISIBLE_COLUMNS = new Set(
  COLUMN_DEFINITIONS.map((c) => c.id).filter((id) => id !== 'created_at')
);

function loadVisibleColumns(): Set<string> {
  try {
    const stored = localStorage.getItem('notes-table-columns');
    if (stored) {
      const parsed = JSON.parse(stored);
      if (!Array.isArray(parsed) || !parsed.every(id => COLUMN_DEFINITIONS.some(col => col.id === id))) {
        return new Set(DEFAULT_VISIBLE_COLUMNS);
      }
      if (Array.isArray(parsed)) {
        return new Set(parsed as string[]);
      }
    }
  } catch {
    // ignore
  }
  return DEFAULT_VISIBLE_COLUMNS;
}

export function NotesListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [showFilters, setShowFilters] = useState(false);
  const [showColumnPicker, setShowColumnPicker] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(loadVisibleColumns);
  const columnPickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (columnPickerRef.current && !columnPickerRef.current.contains(e.target as Node)) {
        setShowColumnPicker(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const toggleColumn = (id: string) => {
    if (id === 'title') return;
    setVisibleColumns((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      try {
        localStorage.setItem('notes-table-columns', JSON.stringify([...next]));
      } catch {
        // quota exceeded or private mode — ignore
      }
      return next;
    });
  };

  // Parse URL params
  const page = parseInt(searchParams.get('page') || '1', 10);
  const state = searchParams.get('state') || '';
  const ownerId = searchParams.get('owner_id') || '';
  const unassigned = searchParams.get('unassigned') === 'true';
  const creatorId = searchParams.get('creator_id') || '';
  const companyId = searchParams.get('company_id') || '';
  const createdAfter = searchParams.get('created_after') || '';
  const createdBefore = searchParams.get('created_before') || '';
  const updatedAfter = searchParams.get('updated_after') || '';
  const updatedBefore = searchParams.get('updated_before') || '';
  const groupBy = searchParams.get('group_by') || '';
  const sort = searchParams.get('sort') || 'created_at';
  const order = (searchParams.get('order') || 'desc') as 'asc' | 'desc';
  const linkedFeature = searchParams.get('linked_feature') || '';

  // Fetch filter options
  const { data: filterOptions } = useQuery({
    queryKey: ['notes', 'filter-options'],
    queryFn: () => notesApi.getFilterOptions().then((r) => r.data),
  });

  const params: NotesParams = {
    page,
    limit: 20,
    sort,
    order,
    ...(state && { state }),
    ...(unassigned && { unassigned: true }),
    ...(!unassigned && ownerId && { owner_id: parseInt(ownerId, 10) }),
    ...(creatorId && { creator_id: parseInt(creatorId, 10) }),
    ...(companyId && { company_id: parseInt(companyId, 10) }),
    ...(createdAfter && { created_after: createdAfter }),
    ...(createdBefore && { created_before: createdBefore }),
    ...(updatedAfter && { updated_after: updatedAfter }),
    ...(updatedBefore && { updated_before: updatedBefore }),
    ...(groupBy && { group_by: groupBy as 'owner' | 'creator' | 'company' }),
    ...(linkedFeature === 'true' && { has_features: true }),
    ...(linkedFeature === 'false' && { has_features: false }),
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

  const clearFilters = () => {
    setSearchParams(new URLSearchParams({ sort: 'created_at', order: 'desc' }));
  };

  const hasActiveFilters = state || ownerId || unassigned || creatorId || companyId || createdAfter || createdBefore || updatedAfter || updatedBefore || linkedFeature;

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Notes</h1>
        <div className="flex items-center space-x-4">
          {/* Toggle Filters Button */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-3 py-2 text-sm border rounded flex items-center space-x-2 ${hasActiveFilters ? 'bg-blue-50 border-blue-300 text-blue-700' : 'hover:bg-gray-50'}`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            <span>Filters{hasActiveFilters ? ' (Active)' : ''}</span>
          </button>

          {/* Columns Button + Dropdown */}
          <div ref={columnPickerRef} className="relative">
            <button
              onClick={() => setShowColumnPicker(!showColumnPicker)}
              className="px-3 py-2 text-sm border rounded flex items-center space-x-2 hover:bg-gray-50"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h18M3 10h18M3 15h18M3 20h18" />
              </svg>
              <span>Columns</span>
            </button>
            {showColumnPicker && (
              <div className="absolute right-0 mt-1 z-10 bg-white border rounded shadow p-3 min-w-[180px]">
                <p className="text-xs font-medium text-gray-500 mb-2">Show columns</p>
                {COLUMN_DEFINITIONS.map((col) => {
                  const isTitle = col.id === 'title';
                  return (
                    <label
                      key={col.id}
                      className={`flex items-center gap-2 py-1 text-sm text-gray-700 ${isTitle ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                    >
                      <input
                        type="checkbox"
                        checked={isTitle || visibleColumns.has(col.id)}
                        disabled={isTitle}
                        onChange={() => toggleColumn(col.id)}
                      />
                      {col.label}
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          {/* Group By */}
          <select
            value={groupBy}
            onChange={(e) => updateParams({ group_by: e.target.value || undefined })}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">No Grouping</option>
            <option value="owner">Group by Owner</option>
            <option value="creator">Group by Creator</option>
            <option value="company">Group by Company</option>
          </select>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-medium text-gray-700">Filters</h3>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Clear all filters
              </button>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* State Filter */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">State</label>
              <select
                value={state}
                onChange={(e) => updateParams({ state: e.target.value || undefined })}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">All States</option>
                {filterOptions?.states.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* Owner Filter */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Owner</label>
              <select
                value={unassigned ? 'unassigned' : ownerId}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === 'unassigned') {
                    updateParams({ unassigned: 'true', owner_id: undefined });
                  } else {
                    updateParams({ owner_id: val || undefined, unassigned: undefined });
                  }
                }}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">All Owners</option>
                <option value="unassigned">Unassigned</option>
                {filterOptions?.owners.map((o) => (
                  <option key={o.id} value={o.id}>{o.name || `User ${o.id}`}</option>
                ))}
              </select>
            </div>

            {/* Creator Filter */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Creator</label>
              <select
                value={creatorId}
                onChange={(e) => updateParams({ creator_id: e.target.value || undefined })}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">All Creators</option>
                {filterOptions?.creators.map((c) => (
                  <option key={c.id} value={c.id}>{c.name || `User ${c.id}`}</option>
                ))}
              </select>
            </div>

            {/* Company Filter */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Company</label>
              <select
                value={companyId}
                onChange={(e) => updateParams({ company_id: e.target.value || undefined })}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">All Companies</option>
                {filterOptions?.companies.map((c) => (
                  <option key={c.id} value={c.id}>{c.name || `Company ${c.id}`}</option>
                ))}
              </select>
            </div>

            {/* Created Date Range */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Created After</label>
              <input
                type="date"
                value={createdAfter}
                onChange={(e) => updateParams({ created_after: e.target.value || undefined })}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Created Before</label>
              <input
                type="date"
                value={createdBefore}
                onChange={(e) => updateParams({ created_before: e.target.value || undefined })}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>

            {/* Updated Date Range */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Updated After</label>
              <input
                type="date"
                value={updatedAfter}
                onChange={(e) => updateParams({ updated_after: e.target.value || undefined })}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Updated Before</label>
              <input
                type="date"
                value={updatedBefore}
                onChange={(e) => updateParams({ updated_before: e.target.value || undefined })}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>

            {/* Feature Link Filter */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Feature Link</label>
              <select
                value={linkedFeature}
                onChange={(e) => updateParams({ linked_feature: e.target.value || undefined })}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">All Features</option>
                <option value="true">Linked</option>
                <option value="false">Not linked</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Results Count */}
      {data && (
        <div className="text-sm text-gray-500 mb-4">
          Showing {data.data.length} of {data.pagination.total} notes
        </div>
      )}

      <NotesTable
        notes={data?.data || []}
        isLoading={isLoading}
        groupedData={data?.grouped_data}
        groupCounts={data?.group_counts}
        groupBy={groupBy}
        sort={sort}
        order={order}
        onSort={(newSort, newOrder) => updateParams({ sort: newSort, order: newOrder })}
        visibleColumns={visibleColumns}
      />

      {data && !groupBy && (
        <Pagination
          page={data.pagination.page}
          totalPages={data.pagination.pages}
          onPageChange={handlePageChange}
        />
      )}
    </div>
  );
}
