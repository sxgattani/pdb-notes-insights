import { apiClient } from './client';

export interface UserWorkload {
  user_id: number;
  name: string;
  email: string;
  total_notes: number;
  unprocessed_notes: number;
  processed_notes: number;
  total_features: number;
}

export interface WorkloadResponse {
  data: UserWorkload[];
  summary: {
    total_users: number;
    total_unprocessed: number;
    total_processed: number;
  };
}

export interface SLASummary {
  total_unprocessed: number;
  breached: number;
  at_risk: number;
  on_track: number;
  sla_compliance_rate: number;
}

export interface SLANote {
  id: number;
  title: string;
  created_at: string;
  days_old: number;
  owner_id: number;
}

export interface SLAResponse {
  summary: SLASummary;
  breached_notes: SLANote[];
  at_risk_notes: SLANote[];
  sla_days: number;
}

export const reportsApi = {
  getWorkload: () =>
    apiClient.get<WorkloadResponse>('/reports/workload'),

  getUserWorkload: (userId: number) =>
    apiClient.get<any>(`/reports/workload/${userId}`),

  getSLA: () =>
    apiClient.get<SLAResponse>('/reports/sla'),

  getSLAByOwner: () =>
    apiClient.get<{ data: any[] }>('/reports/sla/by-owner'),
};
