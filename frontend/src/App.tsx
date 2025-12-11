import React, { useEffect, useState } from 'react';
import { auth } from './services/auth';
import { Login } from './components/Login';
import { Chat } from './components/Chat';
import { Loading } from './components/Loading';
import { AuthStatus, User } from './types';

function App() {
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Check if we just came from OAuth callback (check URL params)
        const urlParams = new URLSearchParams(window.location.search);
        const authSuccess = urlParams.get('auth_success');
        const email = urlParams.get('email');
        
        // If we have email from OAuth callback, store it and verify with backend
        if (authSuccess === 'true' && email) {
          // Clear URL params after reading (for security)
          window.history.replaceState({}, document.title, window.location.pathname);
          
          // Store email temporarily and verify with backend
          // The backend will set the cookie on its domain
          try {
            // Verify with backend - this will set the cookie on backend domain
            const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
            await fetch(`${API_BASE_URL}/api/auth/verify?email=${encodeURIComponent(email)}`, {
              method: 'POST',
              credentials: 'include',
              headers: {
                'Content-Type': 'application/json',
              },
            });
            
            // Now check auth normally
            const status = await auth.checkAuth();
            setAuthStatus(status);
            
            if (status.authenticated) {
              const userData = await auth.getCurrentUser();
              setUser(userData);
            }
          } catch (verifyError) {
            console.error('Verify failed:', verifyError);
            // Fallback: try normal auth check
            const status = await auth.checkAuth();
            setAuthStatus(status);
            if (status.authenticated) {
              const userData = await auth.getCurrentUser();
              setUser(userData);
            }
          }
        } else {
          // Normal auth check
          const status = await auth.checkAuth();
          setAuthStatus(status);
          
          if (status.authenticated) {
            const userData = await auth.getCurrentUser();
            setUser(userData);
          }
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        setAuthStatus({ authenticated: false });
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  if (loading) {
    return <Loading />;
  }

  if (!authStatus?.authenticated || !user) {
    return <Login />;
  }

  return <Chat userEmail={user.user_email} />;
}

export default App;


