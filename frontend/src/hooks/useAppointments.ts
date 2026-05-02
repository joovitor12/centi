import { useState, useEffect, useCallback } from 'react';
import { appointmentsApi, Appointment } from '../services/appointments';

export const useAppointments = () => {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAppointments = useCallback(async () => {
    try {
      setError(null);
      const data = await appointmentsApi.getAll();
      setAppointments(data);
      return data;
    } catch (err: any) {
      setError(err.message || 'Failed to load appointments');
      console.error('Error loading appointments:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAppointments();
  }, [loadAppointments]);

  const refresh = useCallback(async () => {
    await loadAppointments();
  }, [loadAppointments]);

  return {
    appointments,
    loading,
    error,
    refresh,
  };
};

