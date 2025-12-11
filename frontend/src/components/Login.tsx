import React from 'react';
import { auth } from '../services/auth';
import { ThemeToggle } from './ThemeToggle';

export const Login: React.FC = () => {
  const handleLogin = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    try {
      auth.login();
    } catch (error) {
      console.error('Login error:', error);
      alert('Failed to redirect to login. Please check console for details.');
    }
  };

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      flexDirection: 'column',
      gap: '2rem',
      backgroundColor: 'var(--bg-secondary)',
      position: 'relative',
    }}>
      <div style={{
        position: 'absolute',
        top: '1rem',
        right: '1rem',
      }}>
        <ThemeToggle />
      </div>
      <div style={{
        backgroundColor: 'var(--bg-primary)',
        padding: '3rem',
        borderRadius: '8px',
        boxShadow: `0 2px 8px var(--shadow)`,
        textAlign: 'center',
        maxWidth: '400px',
      }}>
        <h1 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>Centi</h1>
        <p style={{ marginBottom: '2rem', color: 'var(--text-secondary)' }}>
          Your smart calendar assistant
        </p>
        <button
          onClick={handleLogin}
          style={{
            backgroundColor: 'var(--accent-color)',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '4px',
            fontSize: '16px',
            cursor: 'pointer',
            fontWeight: '500',
            transition: 'opacity 0.2s',
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.opacity = '0.9';
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.opacity = '1';
          }}
        >
          Sign in with Google
        </button>
      </div>
    </div>
  );
};

