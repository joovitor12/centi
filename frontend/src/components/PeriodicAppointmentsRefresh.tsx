import { useEffect, useRef } from 'react';

interface PeriodicAppointmentsRefreshProps {
  onRefresh: () => void;
}

/**
 * Simple component that periodically refreshes the appointments list.
 * This is more reliable than trying to detect changes via Parlant events
 * due to API timeout issues.
 */
export const PeriodicAppointmentsRefresh: React.FC<PeriodicAppointmentsRefreshProps> = ({
  onRefresh,
}) => {
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Refresh every 3 seconds
    intervalRef.current = setInterval(() => {
      onRefresh();
    }, 3000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [onRefresh]);

  return null;
};

