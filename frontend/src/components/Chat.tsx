import React, { useEffect, useState } from 'react';
import ParlantChatbox from 'parlant-chat-react';
import { auth } from '../services/auth';
import { Session } from '../types';
import { Loading } from './Loading';
import { EmailInteractorGuide } from './EmailInteractorGuide';
import { ThemeToggle } from './ThemeToggle';

interface ChatProps {
  userEmail: string;
}

export const Chat: React.FC<ChatProps> = ({ userEmail }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(() => {
    // Show guide if user hasn't seen it before (stored in localStorage)
    const hasSeenGuide = localStorage.getItem('centi_has_seen_email_guide');
    return !hasSeenGuide;
  });
  useEffect(() => {
    const loadSession = async () => {
      try {
        setLoading(true);
        const sessionData = await auth.getOrCreateSession();
        setSession(sessionData);
        
        // Check if we need to send initial message for this session
        if (sessionData?.session_id) {
          const key = `centi_initial_message_sent_${sessionData.session_id}`;
          const hasSent = localStorage.getItem(key);
          
          // If localStorage was cleared, check if the first message is already our welcome message
          if (!hasSent) {
            try {
              const parlantServerUrl = process.env.REACT_APP_PARLANT_SERVER_URL || 'http://localhost:8800';
              const response = await fetch(`${parlantServerUrl}/sessions/${sessionData.session_id}/events`);
              
              if (response.ok) {
                const events = await response.json();
                // Filter to only message events (ignore system events)
                const messageEvents = Array.isArray(events) 
                  ? events.filter((event: any) => 
                      event.kind === 'message' && 
                      (event.source === 'agent' || event.source === 'customer')
                    )
                  : [];
                
                // Check if first message is our welcome message
                const welcomeMessageStart = "Hi there! 👋";
                const firstAgentMessage = messageEvents.find((e: any) => e.source === 'agent');
                const alreadyHasWelcomeMessage = firstAgentMessage?.message?.startsWith(welcomeMessageStart);
                
                // Only send if session is empty OR first message is not our welcome message
                if (messageEvents.length === 0 || !alreadyHasWelcomeMessage) {
                  // Send initial message via API
                  const welcomeMessage = (
                    "Hi there! 👋\n\n" +
                    "I'm Centi, your calendar assistant. Please note that chat support for creating reminders and appointments directly in your calendar is not yet available. You can use the Email Interactor for that.\n\n" +
                    "📧 **How to use Email Interactor:**\n" +
                    "1. Send an email to the person you want to schedule with\n" +
                    "2. Add **centinteractor@gmail.com** in CC\n" +
                    "3. Mention 'Centi' in your message asking to schedule a meeting\n" +
                    "4. I'll analyze your calendars and suggest available times\n" +
                    "5. Reply confirming your preferred time\n" +
                    "6. I'll create the calendar event and confirm with everyone\n\n" +
                    "For more details, check the 'How to use Email Interactor' guide in the header above.\n\n" +
                    "How can I help you today? 🎉"
                  );
                  
                  const sendResponse = await fetch(`${parlantServerUrl}/sessions/${sessionData.session_id}/events`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                      kind: 'message',
                      source: 'agent',
                      message: welcomeMessage,
                    }),
                  });
                  
                  if (sendResponse.ok) {
                    // Mark as sent only if successfully sent
                    localStorage.setItem(key, 'true');
                    console.log('Initial welcome message sent to session');
                  }
                } else {
                  // First message is already our welcome message, mark as sent
                  localStorage.setItem(key, 'true');
                  console.log('Session already has welcome message, skipping');
                }
              } else {
                console.warn('Failed to fetch session events:', response.status);
              }
            } catch (err) {
              console.warn('Failed to check/send initial message:', err);
            }
          } else {
            console.log('Initial message already sent for this session (from localStorage)');
          }
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load session');
      } finally {
        setLoading(false);
      }
    };

    loadSession();
  }, []);

  if (loading) {
    return <Loading />;
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: 'red' }}>Error: {error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  if (!session) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No session available</p>
      </div>
    );
  }

  // Get Parlant server URL from environment or use default
  const parlantServerUrl = process.env.REACT_APP_PARLANT_SERVER_URL || 'http://localhost:8800';
  const agentId = process.env.REACT_APP_PARLANT_AGENT_ID || 'default';

  const handleCloseGuide = () => {
    setShowGuide(false);
    localStorage.setItem('centi_has_seen_email_guide', 'true');
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-secondary)' }}>
      {showGuide && <EmailInteractorGuide onClose={handleCloseGuide} />}
      
      {/* Header */}
      <div style={{
        padding: '1rem',
        backgroundColor: 'var(--bg-primary)',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: `0 2px 4px var(--shadow)`,
      }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--primary-color)' }}>Centi</h1>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{userEmail}</span>
          <ThemeToggle />
          <button
            onClick={async () => {
              await auth.logout();
              window.location.reload();
            }}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: 'var(--danger-color)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'background-color 0.2s',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--danger-hover)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--danger-color)';
            }}
          >
            Logout
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        textAlign: 'center',
      }}>
        <div style={{
          maxWidth: '600px',
          backgroundColor: 'var(--bg-primary)',
          padding: '3rem',
          borderRadius: '12px',
          boxShadow: `0 4px 6px var(--shadow)`,
        }}>
          <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>📧</div>
          <h2 style={{ margin: '0 0 1rem', color: 'var(--text-primary)', fontSize: '1.8rem' }}>
            Welcome to Centi!
          </h2>
          <p style={{ margin: '0 0 1.5rem', color: 'var(--text-secondary)', fontSize: '1rem', lineHeight: '1.6' }}>
            Centi helps you schedule meetings via email. To get started, check out click the chat button in the bottom right corner if you have questions.
          </p>
          <button
            onClick={() => setShowGuide(true)}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: 'var(--primary-color)',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500',
              transition: 'background-color 0.2s',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--primary-hover)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--primary-color)';
            }}
          >
            📖 View Email Interactor Guide
          </button>
        </div>
      </div>

      {/* Floating Chat Widget */}
      <ParlantChatbox
        server={parlantServerUrl}
        agentId={agentId}
        sessionId={session.session_id}
        float={true}
        components={{
          popupButton: ({ toggleChatOpen }) => (
            <button
              type="button"
              className="custom-parlant-button"
              onClick={toggleChatOpen}
              style={{
                position: 'fixed',
                bottom: '20px',
                right: '20px',
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                backgroundColor: 'var(--primary-color)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                boxShadow: `0 4px 12px var(--shadow-hover)`,
                transition: 'all 0.3s',
                zIndex: 999,
                border: 'none',
                padding: 0,
                margin: 0,
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'scale(1.1)';
                e.currentTarget.style.backgroundColor = 'var(--primary-hover)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.backgroundColor = 'var(--primary-color)';
              }}
            >
              <span style={{ fontSize: '1.5rem' }}>💬</span>
            </button>
          ),
        }}
        classNames={{
          popupButton: 'parlant-chat-popup-button-hidden',
        }}
      />
    </div>
  );
};

