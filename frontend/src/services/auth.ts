import { api } from './api';
import { AuthStatus, User, Session } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const auth = {
  async checkAuth(): Promise<AuthStatus> {
    try {
      return await api.get<AuthStatus>('/api/auth/check');
    } catch (error: any) {
      if (error.message.includes('401')) {
        return { authenticated: false };
      }
      throw error;
    }
  },
  
  async getCurrentUser(): Promise<User> {
    return await api.get<User>('/api/user/me');
  },
  
  async logout(): Promise<void> {
    await api.post('/api/auth/logout');
    // Also clear localStorage
    localStorage.removeItem('centi_user_email');
  },
  
  login(): void {
    // Redirect to OAuth endpoint
    // Use the same API URL configuration as the API client
    const oauthUrl = `${API_BASE_URL}/auth/google`;
    console.log('Redirecting to OAuth:', oauthUrl);
    window.location.href = oauthUrl;
  },
  
  async getOrCreateSession(): Promise<Session> {
    return await api.get<Session>('/api/session/current');
  },
  
  async createSession(): Promise<Session> {
    return await api.post<Session>('/api/session/create');
  },
};

