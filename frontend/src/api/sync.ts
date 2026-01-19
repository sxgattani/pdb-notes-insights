import { apiClient } from './client';

export type SyncStatus = {
  status: 'idle' | 'running';
  entity_type?: string;
  started_at?: string;
};

export const syncApi = {
  trigger: () =>
    apiClient.post<{ message: string; status: string }>('/sync/trigger'),

  getStatus: () =>
    apiClient.get<SyncStatus>('/sync/status'),
};
