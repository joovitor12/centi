import React from 'react';
import { useTheme } from '../contexts/ThemeContext';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      type="button"
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      style={{
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        padding: '0.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '1.5rem',
        transition: 'transform 0.3s ease',
        color: 'inherit',
      }}
      onMouseOver={(e) => {
        e.currentTarget.style.transform = 'scale(1.1) rotate(15deg)';
      }}
      onMouseOut={(e) => {
        e.currentTarget.style.transform = 'scale(1) rotate(0deg)';
      }}
    >
      {theme === 'light' ? '🌙' : '☀️'}
    </button>
  );
};
