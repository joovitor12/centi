import React, { useImperativeHandle, forwardRef } from 'react';
import { useAppointments } from '../hooks/useAppointments';
import { Loading } from './Loading';

export interface AppointmentsListRef {
  refresh: () => Promise<void>;
}

export const AppointmentsList = forwardRef<AppointmentsListRef>((props, ref) => {
  const { appointments, loading, error, refresh } = useAppointments();

  // Expose refresh method to parent component
  useImperativeHandle(ref, () => ({
    refresh,
  }));

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (e) {
      return dateString;
    }
  };

  if (loading) {
    return <Loading />;
  }

  if (error) {
    return (
      <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--danger-color)' }}>
        <p>Error: {error}</p>
        <button
          onClick={() => refresh()}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: 'var(--primary-color)',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (appointments.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-secondary)' }}>No appointments found.</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '1.5rem' }}>
      <h2 style={{ margin: '0 0 1.5rem', color: 'var(--text-primary)', fontSize: '1.5rem' }}>
        Your Appointments
      </h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {appointments.map((appointment) => (
          <div
            key={appointment.id}
            style={{
              backgroundColor: 'var(--bg-primary)',
              padding: '1rem',
              borderRadius: '8px',
              border: `1px solid var(--border-color)`,
              boxShadow: `0 2px 4px var(--shadow)`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
              <h3 style={{ margin: 0, color: 'var(--text-primary)', fontSize: '1.1rem' }}>
                {appointment.description}
              </h3>
              {appointment.google_calendar_event_id && (
                <span
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '4px',
                  }}
                >
                  📅 Synced
                </span>
              )}
            </div>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              {formatDate(appointment.time)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
});

AppointmentsList.displayName = 'AppointmentsList';
