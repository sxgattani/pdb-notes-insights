import { apiClient } from './client';

export type Export = {
  id: number;
  report_type: string;
  format: string;
  filename: string;
  status: string;
  file_size: number | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
};

export type ExportRequest = {
  report_type: 'notes_summary' | 'features_summary' | 'pm_performance' | 'sla_report';
  export_format: 'pdf' | 'json';
};

export const exportsApi = {
  list: (limit = 50, offset = 0) =>
    apiClient.get<{ data: Export[]; total: number }>('/exports', { params: { limit, offset } }),

  trigger: (request: ExportRequest) =>
    apiClient.post<{ export_id: number; status: string }>('/exports', request),

  getDownloadUrl: (exportId: number) =>
    `${apiClient.defaults.baseURL}/exports/${exportId}/download`,
};
