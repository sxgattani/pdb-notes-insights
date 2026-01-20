import { apiClient } from './client';

export type SyncStatus = {
  status: 'idle' | 'running';
  entity_type?: string;
  started_at?: string;
  last_sync_at?: string;
};

export type SyncTriggerResponse = {
  message: string;
  status: string;
  triggered: boolean;
};

export const syncApi = {
  trigger: () =>
    apiClient.post<SyncTriggerResponse>('/sync/trigger'),

  triggerIfNeeded: () =>
    apiClient.post<SyncTriggerResponse>('/sync/trigger-if-needed'),

  getStatus: () =>
    apiClient.get<SyncStatus>('/sync/status'),
};
