import { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table';
import { useNavigate } from 'react-router-dom';
import type { Note } from '../api/notes';

const columnHelper = createColumnHelper<Note>();

interface NotesTableProps {
  notes: Note[];
  isLoading?: boolean;
}

export function NotesTable({ notes, isLoading }: NotesTableProps) {
  const navigate = useNavigate();

  const columns = useMemo(
    () => [
      columnHelper.accessor('title', {
        header: 'Title',
        cell: (info) => (
          <span className="font-medium text-gray-900">
            {info.getValue() || '(No title)'}
          </span>
        ),
      }),
      columnHelper.accessor('type', {
        header: 'Type',
        cell: (info) => (
          <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-700">
            {info.getValue() || '-'}
          </span>
        ),
      }),
      columnHelper.accessor('source', {
        header: 'Source',
        cell: (info) => info.getValue() || '-',
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
