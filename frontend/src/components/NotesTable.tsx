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

interface NotesTableProps {
  notes: Note[];
  isLoading?: boolean;
  groupedData?: Record<string, Note[]> | null;
  groupCounts?: Record<string, number> | null;
  groupBy?: string;
}

export function NotesTable({ notes, isLoading, groupedData, groupCounts, groupBy }: NotesTableProps) {
  const navigate = useNavigate();

  const columns = useMemo(
    () => [
      columnHelper.accessor('company', {
        header: 'Company',
        cell: (info) => {
          const company = info.getValue();
          return company?.name || '-';
        },
      }),
      columnHelper.accessor('title', {
        header: 'Title',
        cell: (info) => {
          const note = info.row.original;
          return (
            <div>
              <span className="font-medium text-gray-900">
                {info.getValue() || '(No title)'}
              </span>
              {note.tags && note.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {note.tags.slice(0, 3).map((tag, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-600"
                    >
                      {tag}
                    </span>
                  ))}
                  {note.tags.length > 3 && (
                    <span className="text-xs text-gray-400">+{note.tags.length - 3}</span>
                  )}
                </div>
              )}
            </div>
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
          return owner.name || owner.email || 'Unassigned';
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
            <div key={groupName} className="bg-white rounded-lg shadow overflow-hidden">
              <div className="bg-gray-100 px-6 py-3 border-b">
                <h3 className="text-sm font-semibold text-gray-700">
                  {groupName} <span className="text-gray-500 font-normal">({totalCount})</span>
                </h3>
              </div>
              <NotesTableBody notes={groupNotes} columns={columns} navigate={navigate} />
            </div>
          );
        })}
      </div>
    );
  }

  // Render flat view
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
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
  navigate
}: {
  notes: Note[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: ColumnDef<Note, any>[];
  navigate: ReturnType<typeof useNavigate>;
}) {
  const table = useReactTable({
    data: notes,
    columns: columns as any,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <table className="min-w-full divide-y divide-gray-200">
      <thead className="bg-gray-50">
        {table.getHeaderGroups().map((headerGroup) => (
          <tr key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <th
                key={header.id}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {flexRender(header.column.columnDef.header, header.getContext())}
              </th>
            ))}
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
