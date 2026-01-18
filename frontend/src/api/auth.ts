import { apiClient } from './client';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface User {
  username: string;
  authenticated: boolean;
}

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<{ message: string; username: string }>('/auth/login', data),

  logout: () =>
    apiClient.post('/auth/logout'),

  me: () =>
    apiClient.get<User>('/auth/me'),
};
