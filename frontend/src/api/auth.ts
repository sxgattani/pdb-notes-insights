import { apiClient } from './client';

export type LoginRequest = {
  username: string;
  password: string;
};

export type User = {
  username: string;
  authenticated: boolean;
};

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<{ message: string; username: string }>('/auth/login', data),

  logout: () =>
    apiClient.post('/auth/logout'),

  me: () =>
    apiClient.get<User>('/auth/me'),
};
