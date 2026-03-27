import { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
  type ColumnDef,
} from '@tanstack/react-table';
import { useNavigate } from 'react-router-dom';
import type { Note } from '../api/notes';

const columnHelper = createColumnHelper<Note>();

// Sort field mapping from column id to backend field
const SORT_FIELDS: Record<string, string> = {
  company: 'company',
  owner: 'owner',
  state: 'state',
  response_time_days: 'response_time',
  updated_at: 'updated_at',
  created_at: 'created_at',
};

// Columns that are sortable (all except title)
const SORTABLE_COLUMNS = new Set(['company', 'owner', 'state', 'response_time_days', 'updated_at', 'created_at']);

interface NotesTableProps {
  notes: Note[];
  isLoading?: boolean;
  groupedData?: Record<string, Note[]> | null;
  groupCounts?: Record<string, number> | null;
  groupBy?: string;
  sort?: string;
  order?: 'asc' | 'desc';
  onSort?: (sort: string, order: 'asc' | 'desc') => void;
}

// Sort indicator component
function SortIndicator({ active, direction }: { active: boolean; direction: 'asc' | 'desc' }) {
  if (!active) {
    return (
      <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
      </svg>
    );
  }
  if (direction === 'asc') {
    return (
      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    );
  }
  return (
    <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

export function NotesTable({ notes, isLoading, groupedData, groupCounts, groupBy, sort, order, onSort }: NotesTableProps) {
  const navigate = useNavigate();

  // Handle column header click for sorting
  const handleSort = (columnId: string) => {
    if (!onSort || !SORTABLE_COLUMNS.has(columnId)) return;

    const sortField = SORT_FIELDS[columnId];
    // If clicking on currently sorted column, toggle direction
    // Otherwise, set new sort with desc as default
    if (sort === sortField) {
      onSort(sortField, order === 'asc' ? 'desc' : 'asc');
    } else {
      onSort(sortField, 'desc');
    }
  };

  // Check if a column is currently being sorted
  const isColumnSorted = (columnId: string) => {
    const sortField = SORT_FIELDS[columnId];
    return sort === sortField;
  };

  const columns = useMemo(
    () => [
      // Column order: Title, Company, Owner, State, Response Time, Updated, Created
      columnHelper.accessor('title', {
        header: 'Title',
        cell: (info) => {
          const note = info.row.original;
          const title = info.getValue() || '(No title)';
          return (
            <div className="max-w-xs">
              <span className="font-medium text-gray-900 block truncate" title={title}>
                {title}
              </span>
              {note.tags && note.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {note.tags.slice(0, 2).map((tag, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-600"
                    >
                      {tag}
                    </span>
                  ))}
                  {note.tags.length > 2 && (
                    <span className="text-xs text-gray-400">+{note.tags.length - 2}</span>
                  )}
                </div>
              )}
            </div>
          );
        },
      }),
      columnHelper.accessor('company', {
        header: 'Company',
        cell: (info) => {
          const company = info.getValue();
          const name = company?.name || '-';
          return (
            <span className="block max-w-[150px] truncate" title={name}>
              {name}
            </span>
          );
        },
      }),
      columnHelper.accessor('owner', {
        header: 'Owner',
        cell: (info) => {
          const owner = info.getValue();
          if (!owner) {
            return <span className="text-gray-400">Unassigned</span>;
          }
          const name = owner.name || owner.email || 'Unassigned';
          return (
            <span className="block max-w-[120px] truncate" title={name}>
              {name}
            </span>
          );
        },
      }),
      columnHelper.accessor('state', {
        header: 'State',
        cell: (info) => {
          const state = info.getValue();
          const colors = state === 'processed'
            ? 'bg-green-100 text-green-800'
            : 'bg-yellow-100 text-yellow-800';
          return (
            <span className={`px-2 py-1 text-xs rounded-full ${colors}`}>
              {state}
            </span>
          );
        },
      }),
      columnHelper.accessor('has_features', {
        header: 'Linked Feature',
        cell: (info) => {
          const hasFeatures = info.getValue();
          if (hasFeatures) {
            return (
              <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                Linked
              </span>
            );
          }
          return (
            <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-500">
              Unlinked
            </span>
          );
        },
      }),
      columnHelper.accessor('response_time_days', {
        header: 'Response Time',
        cell: (info) => {
          const rt = info.getValue();
          const state = info.row.original.state;
          if (rt !== null) {
            const color = rt <= 3 ? 'text-green-600' : rt <= 5 ? 'text-yellow-600' : 'text-red-600';
            return <span className={`font-medium ${color}`}>{rt.toFixed(1)}d</span>;
          }
          return state === 'unprocessed' ? (
            <span className="text-gray-400">pending</span>
          ) : (
            <span className="text-gray-400">-</span>
          );
        },
      }),
      columnHelper.accessor('updated_at', {
        header: 'Updated',
        cell: (info) => {
          const date = info.getValue();
          return date ? new Date(date).toLocaleDateString() : '-';
        },
      }),
      columnHelper.accessor('created_at', {
        header: 'Created',
        cell: (info) => {
          const date = info.getValue();
          return date ? new Date(date).toLocaleDateString() : '-';
        },
      }),
    ],
    []
  );

  const table = useReactTable({
    data: notes,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        Loading notes...
      </div>
    );
  }

  if (notes.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No notes found
      </div>
    );
  }

  // Render grouped view
  if (groupedData && groupBy) {
    // Sort groups by total count (from groupCounts) descending, then alphabetically
    const groups = Object.entries(groupedData).sort(([a], [b]) => {
      const countA = groupCounts?.[a] ?? 0;
      const countB = groupCounts?.[b] ?? 0;
      if (countB !== countA) return countB - countA;
      return a.localeCompare(b);
    });
    return (
      <div className="space-y-6">
        {groups.map(([groupName, groupNotes]) => {
          // Use accurate count from groupCounts, fallback to array length
          const totalCount = groupCounts?.[groupName] ?? groupNotes.length;
          return (
            <div key={groupName} className="bg-white rounded-lg shadow overflow-x-auto">
              <div className="bg-gray-100 px-6 py-3 border-b">
                <h3 className="text-sm font-semibold text-gray-700">
                  {groupName} <span className="text-gray-500 font-normal">({totalCount})</span>
                </h3>
              </div>
              <NotesTableBody notes={groupNotes} columns={columns} navigate={navigate} sort={sort} order={order} onSort={onSort} />
            </div>
          );
        })}
      </div>
    );
  }

  // Render flat view
  return (
    <div className="bg-white rounded-lg shadow overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const isSortable = SORTABLE_COLUMNS.has(header.id);
                const isSorted = isColumnSorted(header.id);
                return (
                  <th
                    key={header.id}
                    onClick={() => isSortable && handleSort(header.id)}
                    className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      isSortable ? 'cursor-pointer hover:bg-gray-100 select-none' : ''
                    }`}
                  >
                    <div className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {isSortable && (
                        <SortIndicator active={isSorted} direction={order || 'desc'} />
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => navigate(`/notes/${row.original.id}`)}
              className="hover:bg-gray-50 cursor-pointer"
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Helper component for grouped table body
function NotesTableBody({
  notes,
  columns,
  navigate,
  sort,
  order,
  onSort,
}: {
  notes: Note[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: ColumnDef<Note, any>[];
  navigate: ReturnType<typeof useNavigate>;
  sort?: string;
  order?: 'asc' | 'desc';
  onSort?: (sort: string, order: 'asc' | 'desc') => void;
}) {
  const table = useReactTable({
    data: notes,
    columns: columns as any,
    getCoreRowModel: getCoreRowModel(),
  });

  const handleSort = (columnId: string) => {
    if (!onSort || !SORTABLE_COLUMNS.has(columnId)) return;
    const sortField = SORT_FIELDS[columnId];
    if (sort === sortField) {
      onSort(sortField, order === 'asc' ? 'desc' : 'asc');
    } else {
      onSort(sortField, 'desc');
    }
  };

  const isColumnSorted = (columnId: string) => {
    const sortField = SORT_FIELDS[columnId];
    return sort === sortField;
  };

  return (
    <table className="min-w-full divide-y divide-gray-200">
      <thead className="bg-gray-50">
        {table.getHeaderGroups().map((headerGroup) => (
          <tr key={headerGroup.id}>
            {headerGroup.headers.map((header) => {
              const isSortable = SORTABLE_COLUMNS.has(header.id);
              const isSorted = isColumnSorted(header.id);
              return (
                <th
                  key={header.id}
                  onClick={() => isSortable && handleSort(header.id)}
                  className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                    isSortable ? 'cursor-pointer hover:bg-gray-100 select-none' : ''
                  }`}
                >
                  <div className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {isSortable && (
                      <SortIndicator active={isSorted} direction={order || 'desc'} />
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        ))}
      </thead>
      <tbody className="bg-white divide-y divide-gray-200">
        {table.getRowModel().rows.map((row) => (
          <tr
            key={row.id}
            onClick={() => navigate(`/notes/${row.original.id}`)}
            className="hover:bg-gray-50 cursor-pointer"
          >
            {row.getVisibleCells().map((cell) => (
              <td key={cell.id} className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
