import { apiClient, PaginatedResponse } from './client';

export interface Feature {
  id: number;
  pb_id: string;
  name: string;
  description: string;
  type: string;
  status: string;
  product_area: string;
  product_area_stack_rank: number | null;
  committed: boolean;
  risk: string;
  owner_id: number | null;
  created_at: string | null;
  note_count: number;
}

export interface FeaturesStats {
  total: number;
  committed: number;
  uncommitted: number;
  by_product_area: Record<string, number>;
  by_risk: Record<string, number>;
}

export interface FeaturesParams {
  page?: number;
  limit?: number;
  product_area?: string;
  owner_id?: number;
  committed?: boolean;
  sort?: string;
  order?: 'asc' | 'desc';
}

export const featuresApi = {
  list: (params: FeaturesParams = {}) =>
    apiClient.get<PaginatedResponse<Feature>>('/features', { params }),

  get: (id: number) =>
    apiClient.get<Feature & { notes: Array<{ id: number; title: string; state: string; created_at: string | null }> }>(`/features/${id}`),

  getStats: () =>
    apiClient.get<FeaturesStats>('/features/stats'),
};
