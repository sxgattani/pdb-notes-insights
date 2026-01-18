import { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table';
import { useNavigate } from 'react-router-dom';
import type { Feature } from '../api/features';

const columnHelper = createColumnHelper<Feature>();

interface FeaturesTableProps {
  features: Feature[];
  isLoading?: boolean;
}

export function FeaturesTable({ features, isLoading }: FeaturesTableProps) {
  const navigate = useNavigate();

  const columns = useMemo(
    () => [
      columnHelper.accessor('name', {
        header: 'Name',
        cell: (info) => (
          <span className="font-medium text-gray-900">
            {info.getValue() || '(No name)'}
          </span>
        ),
      }),
      columnHelper.accessor('product_area', {
        header: 'Product Area',
        cell: (info) => (
          <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700">
            {info.getValue() || '-'}
          </span>
        ),
      }),
      columnHelper.accessor('status', {
        header: 'Status',
        cell: (info) => info.getValue() || '-',
      }),
      columnHelper.accessor('committed', {
        header: 'Committed',
        cell: (info) => {
          const committed = info.getValue();
          return committed ? (
            <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Yes</span>
          ) : (
            <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600">No</span>
          );
        },
      }),
      columnHelper.accessor('risk', {
        header: 'Risk',
        cell: (info) => {
          const risk = info.getValue();
          if (!risk) return '-';
          const colors: Record<string, string> = {
            high: 'bg-red-100 text-red-800',
            medium: 'bg-yellow-100 text-yellow-800',
            low: 'bg-green-100 text-green-800',
          };
          return (
            <span className={`px-2 py-1 text-xs rounded-full ${colors[risk.toLowerCase()] || 'bg-gray-100 text-gray-600'}`}>
              {risk}
            </span>
          );
        },
      }),
      columnHelper.accessor('note_count', {
        header: 'Notes',
        cell: (info) => info.getValue() || 0,
      }),
    ],
    []
  );

  const table = useReactTable({
    data: features,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        Loading features...
      </div>
    );
  }

  if (features.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No features found
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
              onClick={() => navigate(`/features/${row.original.id}`)}
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
