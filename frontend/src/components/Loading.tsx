import React from 'react';

export const Loading: React.FC = () => {
  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh',
      flexDirection: 'column',
      gap: '1rem',
      backgroundColor: 'var(--bg-secondary)',
    }}>
      <div style={{ 
        width: '40px', 
        height: '40px', 
        border: `4px solid var(--border-color)`,
        borderTop: `4px solid var(--primary-color)`,
        borderRadius: '50%',
        animation: 'spin 1s linear infinite'
      }} />
      <p style={{ color: 'var(--text-primary)' }}>Loading...</p>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

