import { useEffect, useRef } from 'react';

interface ParlantEventListenerProps {
  sessionId: string;
  onAppointmentChange: () => void;
}

/**
 * Component that monitors Parlant session events for appointment changes
 * and triggers a refresh callback when appointments are created/edited/deleted.
 */
export const ParlantEventListener: React.FC<ParlantEventListenerProps> = ({
  sessionId,
  onAppointmentChange,
}) => {
  const lastEventOffsetRef = useRef<number>(0);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const parlantServerUrl = process.env.REACT_APP_PARLANT_SERVER_URL || 'http://localhost:8800';

    const checkForAppointmentChanges = async () => {
      try {
        // Poll for new events from Parlant session
        const response = await fetch(
          `${parlantServerUrl}/sessions/${sessionId}/events?minOffset=${lastEventOffsetRef.current}&kinds=message,status`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );

        if (!response.ok) {
          return;
        }

        const events = await response.json();
        if (!Array.isArray(events) || events.length === 0) {
          return;
        }

        // Check if any event indicates appointment changes
        // Look for messages that mention appointment operations
        const appointmentKeywords = [
          'appointment',
          'reminder',
          'scheduled',
          'created',
          'updated',
          'deleted',
          'removed',
          'cancelled',
          'meeting',
          'set for',
          'is set',
          'have been',
          'no upcoming',
        ];

        // Check all events and collect all agent messages
        const agentMessages = events
          .filter((event: any) => event.kind === 'message' && event.source === 'agent')
          .map((event: any) => event.message || event.data?.message || '')
          .join(' ')
          .toLowerCase();

        // Check if any of the keywords or phrases appear in any agent message
        const containsKeyword = appointmentKeywords.some(keyword => agentMessages.includes(keyword));
        const appointmentPhrases = [
          'is set for',
          'has been set',
          'has been deleted',
          'has been removed',
          'have been deleted',
          'have been removed',
          'no appointments',
          'no upcoming',
          'no other appointments',
          'all your appointments',
          'sure thing',
          'got it',
        ];
        const containsPhrase = appointmentPhrases.some(phrase => agentMessages.includes(phrase));
        
        const hasAppointmentChange = containsKeyword || containsPhrase;
        
        if (hasAppointmentChange) {
          console.log('📝 Appointment-related messages detected in events:', events.length);
          console.log('📄 Agent messages:', agentMessages.substring(0, 200));
          console.log('🔑 Contains keyword:', containsKeyword, 'Contains phrase:', containsPhrase);
        }

        if (hasAppointmentChange) {
          console.log('✅ Appointment change detected, refreshing list in 1 second...');
          // Small delay to ensure backend has processed the change
          setTimeout(() => {
            console.log('🔄 Calling onAppointmentChange callback...');
            try {
              onAppointmentChange();
              console.log('✅ Callback executed successfully');
            } catch (error) {
              console.error('❌ Error in onAppointmentChange callback:', error);
            }
          }, 1000);
        }

        // Update last offset to track which events we've already processed
        const lastEvent = events[events.length - 1];
        if (lastEvent && lastEvent.offset !== undefined) {
          const newOffset = lastEvent.offset + 1;
          if (newOffset > lastEventOffsetRef.current) {
            lastEventOffsetRef.current = newOffset;
            console.log('📊 Updated event offset to:', newOffset, '(processed', events.length, 'events)');
          }
        }
      } catch (error) {
        // Silently handle errors (network issues, etc.)
        console.debug('Error checking Parlant events:', error);
      }
    };

    // Start polling every 1 second when session is active (more frequent for better real-time feel)
    pollingIntervalRef.current = setInterval(checkForAppointmentChanges, 1000);

    // Also check immediately
    checkForAppointmentChanges();

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [sessionId, onAppointmentChange]);

  return null;
};

