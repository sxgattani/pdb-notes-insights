import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { exportsApi, Export, ExportRequest } from '../api/exports';

const REPORT_TYPES: { value: ExportRequest['report_type']; label: string }[] = [
  { value: 'notes_summary', label: 'Notes Summary' },
  { value: 'features_summary', label: 'Features Summary' },
  { value: 'pm_performance', label: 'PM Performance' },
  { value: 'sla_report', label: 'SLA Report' },
];

const FORMAT_OPTIONS: { value: ExportRequest['export_format']; label: string }[] = [
  { value: 'pdf', label: 'PDF' },
  { value: 'json', label: 'JSON' },
];

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString();
}

function formatFileSize(bytes: number | null): string {
  if (bytes === null) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getStatusBadge(status: string): { className: string; label: string } {
  switch (status) {
    case 'completed':
      return { className: 'bg-green-100 text-green-800', label: 'Completed' };
    case 'generating':
      return { className: 'bg-blue-100 text-blue-800', label: 'Generating' };
    case 'pending':
      return { className: 'bg-yellow-100 text-yellow-800', label: 'Pending' };
    case 'failed':
      return { className: 'bg-red-100 text-red-800', label: 'Failed' };
    default:
      return { className: 'bg-gray-100 text-gray-800', label: status };
  }
}

function formatReportType(reportType: string): string {
  return reportType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function ExportsPage() {
  const queryClient = useQueryClient();
  const [reportType, setReportType] = useState<ExportRequest['report_type']>('notes_summary');
  const [exportFormat, setExportFormat] = useState<ExportRequest['export_format']>('pdf');

  // Check if any export is pending or generating
  const hasPendingExports = (exports: Export[] | undefined) =>
    exports?.some((e) => e.status === 'pending' || e.status === 'generating') ?? false;

  const { data, isLoading } = useQuery({
    queryKey: ['exports'],
    queryFn: () => exportsApi.list().then((r) => r.data),
    refetchInterval: (query) => (hasPendingExports(query.state.data?.data) ? 5000 : false),
  });

  const triggerMutation = useMutation({
    mutationFn: (request: ExportRequest) => exportsApi.trigger(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exports'] });
    },
  });

  const handleGenerateExport = () => {
    triggerMutation.mutate({ report_type: reportType, export_format: exportFormat });
  };

  const handleDownload = (exportItem: Export) => {
    window.open(exportsApi.getDownloadUrl(exportItem.id), '_blank');
  };

  const exports = data?.data || [];

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Exports</h1>

      {/* Export Trigger Section */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Generate New Export</h2>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label htmlFor="report-type" className="block text-sm font-medium text-gray-700 mb-1">
              Report Type
            </label>
            <select
              id="report-type"
              value={reportType}
              onChange={(e) => setReportType(e.target.value as ExportRequest['report_type'])}
              className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border px-3 py-2"
            >
              {REPORT_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="format" className="block text-sm font-medium text-gray-700 mb-1">
              Format
            </label>
            <select
              id="format"
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as ExportRequest['export_format'])}
              className="block w-32 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border px-3 py-2"
            >
              {FORMAT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={handleGenerateExport}
            disabled={triggerMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {triggerMutation.isPending ? 'Generating...' : 'Generate Export'}
          </button>
        </div>
        {triggerMutation.isError && (
          <p className="mt-2 text-sm text-red-600">
            Failed to trigger export. Please try again.
          </p>
        )}
        {triggerMutation.isSuccess && (
          <p className="mt-2 text-sm text-green-600">
            Export triggered successfully. It will appear in the list below.
          </p>
        )}
      </div>

      {/* Recent Exports Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Exports</h2>
        </div>
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading exports...</div>
        ) : (
          <>
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Report Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Format
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Created
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Size
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {exports.map((exportItem) => {
                  const statusBadge = getStatusBadge(exportItem.status);
                  return (
                    <tr key={exportItem.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                        {formatReportType(exportItem.report_type)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 uppercase">
                        {exportItem.format}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusBadge.className}`}
                        >
                          {statusBadge.label}
                        </span>
                        {exportItem.error_message && (
                          <span className="ml-2 text-xs text-red-600" title={exportItem.error_message}>
                            (hover for details)
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(exportItem.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                        {formatFileSize(exportItem.file_size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                        {exportItem.status === 'completed' ? (
                          <button
                            onClick={() => handleDownload(exportItem)}
                            className="text-blue-600 hover:text-blue-800 font-medium"
                          >
                            Download
                          </button>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {exports.length === 0 && (
              <div className="p-8 text-center text-gray-500">
                No exports yet. Generate your first export above.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
