import { apiClient, PaginatedResponse } from './client';

export interface Note {
  id: number;
  pb_id: string;
  title: string;
  content: string;
  type: string;
  source: string;
  state: string;
  created_at: string | null;
  processed_at: string | null;
  owner_id: number | null;
  customer_id: number | null;
}

export interface NotesStats {
  total: number;
  processed: number;
  unprocessed: number;
  by_type: Record<string, number>;
  by_source: Record<string, number>;
}

export interface NotesParams {
  page?: number;
  limit?: number;
  state?: string;
  owner_id?: number;
  customer_id?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export const notesApi = {
  list: (params: NotesParams = {}) =>
    apiClient.get<PaginatedResponse<Note>>('/notes', { params }),

  get: (id: number) =>
    apiClient.get<Note & { features: Array<{ id: number; name: string; product_area: string }> }>(`/notes/${id}`),

  getStats: () =>
    apiClient.get<NotesStats>('/notes/stats'),
};
