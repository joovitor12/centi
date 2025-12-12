import { api } from './api';

export interface Appointment {
  id: number;
  description: string;
  time: string;
  user_email: string;
  google_calendar_event_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AppointmentsResponse {
  appointments: Appointment[];
}

export const appointmentsApi = {
  async getAll(): Promise<Appointment[]> {
    const response = await api.get<AppointmentsResponse>('/api/appointments');
    return response.appointments;
  },
};

