import { apiClient } from './client';

export type UserWorkload = {
  user_id: number;
  name: string;
  email: string;
  total_notes: number;
  unprocessed_notes: number;
  processed_notes: number;
};

export type WorkloadResponse = {
  data: UserWorkload[];
  summary: {
    total_users: number;
    total_unprocessed: number;
    total_processed: number;
  };
};

export type SLASummary = {
  total_unprocessed: number;
  breached: number;
  at_risk: number;
  on_track: number;
  sla_compliance_rate: number;
};

export type SLANote = {
  id: number;
  title: string;
  created_at: string;
  days_old: number;
  owner_id: number | null;
  owner_name: string | null;
  company_id: number | null;
  company_name: string | null;
};

export type SLAByOwner = {
  id: number;
  name: string;
  breached: number;
  at_risk: number;
  on_track: number;
  compliance_rate: number;
};

export type SLAResponse = {
  summary: SLASummary;
  breached_notes: SLANote[];
  at_risk_notes: SLANote[];
  by_owner: SLAByOwner[];
  sla_days: number;
};

export type StatWithChange = {
  value: number;
  change: number | null;
};

export type FloatStatWithChange = {
  value: number | null;
  change: number | null;
};

export type NotesInsightsSummary = {
  created: StatWithChange;
  processed: StatWithChange;
  unprocessed: StatWithChange;
  unassigned: StatWithChange;
  avg_response_time: FloatStatWithChange;
};

export type OwnerStats = {
  id: number;
  name: string;
  email: string;
  assigned: number;
  processed: number;
  unprocessed: number;
  progress: number;
  avg_response_time: number | null;
  sla_breached: number;
};

export type NotesInsightsResponse = {
  period_days: number;
  summary: NotesInsightsSummary;
  by_owner: OwnerStats[];
};

export type NotesTrendData = {
  week: string;
  created: number;
  processed: number;
};

export type NotesTrendResponse = {
  data: NotesTrendData[];
};

export type ResponseTimeDistribution = {
  bucket: string;
  count: number;
};

export type ResponseTimeByOwner = {
  id: number;
  name: string;
  avg_response_time: number;
  count: number;
};

export type ResponseTimeResponse = {
  average_days: number | null;
  median_days: number | null;
  distribution: ResponseTimeDistribution[];
  by_owner: ResponseTimeByOwner[];
};

export const reportsApi = {
  getWorkload: () =>
    apiClient.get<WorkloadResponse>('/reports/workload'),

  getUserWorkload: (userId: number) =>
    apiClient.get<any>(`/reports/workload/${userId}`),

  getSLA: (days?: number) =>
    apiClient.get<SLAResponse>('/reports/sla', { params: days ? { days } : undefined }),

  getSLAByOwner: () =>
    apiClient.get<{ data: any[] }>('/reports/sla/by-owner'),

  getNotesInsights: (days: number = 90) =>
    apiClient.get<NotesInsightsResponse>('/reports/notes-insights', { params: { days } }),

  getNotesTrend: (days: number = 90) =>
    apiClient.get<NotesTrendResponse>('/reports/notes-trend', { params: { days } }),

  getResponseTime: (days: number = 90) =>
    apiClient.get<ResponseTimeResponse>('/reports/response-time', { params: { days } }),
};
