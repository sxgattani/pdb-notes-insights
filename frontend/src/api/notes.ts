import { apiClient } from './client';
import type { PaginatedResponse } from './client';

export type MemberRef = {
  id: number;
  name: string | null;
  email: string;
};

export type CompanyRef = {
  id: number;
  name: string | null;
};

export type FeatureRef = {
  id: number;
  pb_id: string;
  name: string | null;
  display_url: string | null;
  importance: string | null;
};

export type CommentRef = {
  id: number;
  content: string;
  timestamp: string | null;
  member: MemberRef | null;
};

export type Note = {
  id: number;
  pb_id: string;
  title: string;
  content: string;
  state: string;
  source_origin: string | null;
  display_url: string | null;
  external_display_url: string | null;
  tags: string[];
  followers_count: number;
  created_at: string | null;
  updated_at: string | null;
  processed_at: string | null;
  response_time_days: number | null;
  owner_id: number | null;
  created_by_id: number | null;
  company_id: number | null;
  owner: MemberRef | null;
  creator: MemberRef | null;
  company: CompanyRef | null;
};

export type NoteDetail = Note & {
  features: FeatureRef[];
  comments: CommentRef[];
};

export type NotesStats = {
  total: number;
  processed: number;
  unprocessed: number;
  avg_response_time_days: number | null;
  by_source: Record<string, number>;
};

export type NotesParams = {
  page?: number;
  limit?: number;
  state?: string;
  owner_id?: number;
  creator_id?: number;
  company_id?: number;
  created_after?: string;
  created_before?: string;
  updated_after?: string;
  updated_before?: string;
  group_by?: 'owner' | 'creator' | 'company';
  sort?: string;
  order?: 'asc' | 'desc';
};

export type FilterOption = {
  id: number;
  name: string | null;
};

export type FilterOptions = {
  owners: FilterOption[];
  creators: FilterOption[];
  companies: FilterOption[];
  states: string[];
};

export type NotesResponse = PaginatedResponse<Note> & {
  grouped_data: Record<string, Note[]> | null;
};

export const notesApi = {
  list: (params: NotesParams = {}) =>
    apiClient.get<NotesResponse>('/notes', { params }),

  get: (id: number) =>
    apiClient.get<NoteDetail>(`/notes/${id}`),

  getStats: () =>
    apiClient.get<NotesStats>('/notes/stats'),

  getFilterOptions: () =>
    apiClient.get<FilterOptions>('/notes/filter-options'),
};
