import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';

interface EmailInteractorGuideProps {
  onClose?: () => void;
}

export const EmailInteractorGuide: React.FC<EmailInteractorGuideProps> = ({ onClose }) => {
  const { theme } = useTheme();
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    {
      title: '1. Send an Email',
      description: 'Send an email to the person you want to schedule a meeting with',
      icon: '📧',
      example: {
        to: 'your-contact@example.com',
        cc: 'centinteractor@gmail.com',
        subject: 'Meeting about project',
        body: 'Hi Centi, I need to schedule a meeting to discuss unit tests. Can you suggest some available times?',
      },
    },
    {
      title: '2. Centi Suggests Times',
      description: 'Centi analyzes your calendars and suggests available time slots',
      icon: '📅',
      example: {
        from: 'centinteractor@gmail.com',
        body: 'Hi everyone! I found some available times:\n\n1. Wednesday, December 10 at 1:30 PM\n2. Thursday, December 11 at 9:00 AM\n\nWhich works better for you?',
      },
    },
    {
      title: '3. You Confirm',
      description: 'Reply to the email confirming your preferred time',
      icon: '✅',
      example: {
        body: 'Thursday at 9:00 AM works perfectly!',
      },
    },
    {
      title: '4. Centi Confirms the Meeting',
      description: 'Centi creates the calendar event and confirms with everyone',
      icon: '🎉',
      example: {
        from: 'centinteractor@gmail.com',
        body: 'Perfect! The meeting has been confirmed:\n\n📅 Date: Thursday, December 11\n⏰ Time: 9:00 AM - 9:30 AM\n📋 Topic: Discuss unit tests\n\nI\'ve created a calendar event and sent invitations. See you then!',
      },
    },
  ];

  const nextStep = () => {
    if (activeStep < steps.length - 1) {
      setActiveStep(activeStep + 1);
    }
  };

  const prevStep = () => {
    if (activeStep > 0) {
      setActiveStep(activeStep - 1);
    }
  };

  const currentStep = steps[activeStep];

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '1rem',
    }}>
      <div style={{
        backgroundColor: 'var(--bg-primary)',
        borderRadius: '12px',
        maxWidth: '800px',
        width: '100%',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: `0 20px 60px var(--shadow-hover)`,
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{
          padding: '2rem 2rem 1rem',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.8rem', color: 'var(--primary-color)' }}>
              How to use Email Interactor
            </h2>
            <p style={{ margin: '0.5rem 0 0', color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              Learn how Centi helps you schedule meetings via email
            </p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '1.5rem',
                cursor: 'pointer',
                color: 'var(--text-secondary)',
                padding: '0.5rem',
                lineHeight: 1,
              }}
            >
              ×
            </button>
          )}
        </div>

        {/* Progress Bar */}
        <div style={{
          padding: '1rem 2rem',
          backgroundColor: 'var(--bg-secondary)',
        }}>
          <div style={{
            display: 'flex',
            gap: '0.5rem',
            marginBottom: '0.5rem',
          }}>
            {steps.map((_, index) => (
              <div
                key={index}
                style={{
                  flex: 1,
                  height: '4px',
                  backgroundColor: index <= activeStep ? 'var(--primary-color)' : 'var(--border-color)',
                  borderRadius: '2px',
                  transition: 'background-color 0.3s',
                }}
              />
            ))}
          </div>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
          }}>
            {steps.map((step, index) => (
              <span
                key={index}
                style={{
                  color: index === activeStep ? 'var(--primary-color)' : 'var(--text-tertiary)',
                  fontWeight: index === activeStep ? '600' : '400',
                }}
              >
                {step.title}
              </span>
            ))}
          </div>
        </div>

        {/* Content */}
        <div style={{
          padding: '2rem',
          flex: 1,
        }}>
          <div style={{
            textAlign: 'center',
            marginBottom: '2rem',
          }}>
            <div style={{
              fontSize: '4rem',
              marginBottom: '1rem',
            }}>
              {currentStep.icon}
            </div>
            <h3 style={{
              margin: 0,
              fontSize: '1.5rem',
              color: 'var(--text-primary)',
              marginBottom: '0.5rem',
            }}>
              {currentStep.title}
            </h3>
            <p style={{
              margin: 0,
              color: 'var(--text-secondary)',
              fontSize: '1rem',
            }}>
              {currentStep.description}
            </p>
          </div>

          {/* Email Example */}
          <div style={{
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            overflow: 'hidden',
            backgroundColor: 'var(--bg-tertiary)',
          }}>
            {/* Email Header */}
            <div style={{
              padding: '1rem',
              backgroundColor: 'var(--bg-primary)',
              borderBottom: '1px solid var(--border-color)',
            }}>
              {currentStep.example.from && (
                <div style={{ marginBottom: '0.5rem' }}>
                  <strong style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>From: </strong>
                  <span style={{ color: 'var(--primary-color)' }}>{currentStep.example.from}</span>
                </div>
              )}
              {currentStep.example.to && (
                <div style={{ marginBottom: '0.5rem' }}>
                  <strong style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>To: </strong>
                  <span>{currentStep.example.to}</span>
                </div>
              )}
              {currentStep.example.cc && (
                <div style={{ marginBottom: '0.5rem' }}>
                  <strong style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>CC: </strong>
                  <span style={{ color: 'var(--danger-color)', fontWeight: '600' }}>
                    {currentStep.example.cc}
                  </span>
                  <span style={{
                    marginLeft: '0.5rem',
                    fontSize: '0.85rem',
                    color: 'var(--danger-color)',
                    backgroundColor: theme === 'dark' ? 'rgba(239, 83, 80, 0.2)' : '#ffebee',
                    padding: '0.2rem 0.5rem',
                    borderRadius: '4px',
                  }}>
                    ⚡ Important!
                  </span>
                </div>
              )}
              {currentStep.example.subject && (
                <div>
                  <strong style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Subject: </strong>
                  <span>{currentStep.example.subject}</span>
                </div>
              )}
            </div>

            {/* Email Body */}
            <div style={{
              padding: '1.5rem',
              whiteSpace: 'pre-line',
              lineHeight: '1.6',
              color: 'var(--text-primary)',
            }}>
              {currentStep.example.body}
            </div>
          </div>

          {/* Tip */}
          {activeStep === 0 && (
            <div style={{
              marginTop: '1.5rem',
              padding: '1rem',
              backgroundColor: theme === 'dark' ? 'rgba(66, 165, 245, 0.2)' : '#e3f2fd',
              borderRadius: '8px',
              borderLeft: `4px solid var(--primary-color)`,
            }}>
              <strong style={{ color: 'var(--primary-color)' }}>💡 Tip:</strong>
              <span style={{ marginLeft: '0.5rem', color: 'var(--primary-hover)' }}>
                Always include <code style={{
                  backgroundColor: 'var(--bg-primary)',
                  padding: '0.2rem 0.4rem',
                  borderRadius: '4px',
                  fontFamily: 'monospace',
                  border: `1px solid var(--border-color)`,
                }}>centinteractor@gmail.com</code> in CC and mention "Centi" in your message!
              </span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div style={{
          padding: '1.5rem 2rem',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'var(--bg-tertiary)',
        }}>
          <button
            onClick={prevStep}
            disabled={activeStep === 0}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: activeStep === 0 ? 'var(--border-color)' : 'var(--primary-color)',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: activeStep === 0 ? 'not-allowed' : 'pointer',
              fontSize: '1rem',
              fontWeight: '500',
              opacity: activeStep === 0 ? 0.5 : 1,
            }}
          >
            ← Previous
          </button>

          <div style={{
            fontSize: '0.9rem',
            color: 'var(--text-secondary)',
          }}>
            Step {activeStep + 1} of {steps.length}
          </div>

          {activeStep < steps.length - 1 ? (
            <button
              onClick={nextStep}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: 'var(--primary-color)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: '500',
              }}
            >
              Next →
            </button>
          ) : (
            <button
              onClick={onClose}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: '#4caf50',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: '500',
              }}
            >
              Got it! Start using
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

