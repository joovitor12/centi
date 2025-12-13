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
          console.log('OAuth callback detected, email:', email);
          
          // Store email in sessionStorage as backup (for mobile Safari issues)
          sessionStorage.setItem('centi_oauth_email', email);
          
          // Clear URL params after reading (for security)
          window.history.replaceState({}, document.title, window.location.pathname);
          
          // Store email temporarily and verify with backend
          // The backend will set the cookie on its domain
          try {
            // Verify with backend - this will set the cookie on backend domain
            const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
            console.log('Verifying auth with backend...');
            const verifyResponse = await fetch(`${API_BASE_URL}/api/auth/verify?email=${encodeURIComponent(email)}`, {
              method: 'POST',
              credentials: 'include',
              headers: {
                'Content-Type': 'application/json',
              },
            });
            
            if (!verifyResponse.ok) {
              const errorText = await verifyResponse.text();
              console.error('Verify response not OK:', verifyResponse.status, errorText);
            } else {
              console.log('Verify successful');
            }
            
            // Wait a bit for cookie to be set (especially important on mobile)
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Now check auth normally
            console.log('Checking auth...');
            const status = await auth.checkAuth();
            console.log('Auth status:', status);
            setAuthStatus(status);
            
            if (status.authenticated) {
              const userData = await auth.getCurrentUser();
              console.log('User data:', userData);
              setUser(userData);
              // Clear backup email after successful auth
              sessionStorage.removeItem('centi_oauth_email');
            } else {
              // If auth check failed but we have email, retry once after a delay
              console.warn('Auth check failed after verify, retrying...');
              await new Promise(resolve => setTimeout(resolve, 1000));
              const retryStatus = await auth.checkAuth();
              if (retryStatus.authenticated) {
                const userData = await auth.getCurrentUser();
                setUser(userData);
                setAuthStatus(retryStatus);
                sessionStorage.removeItem('centi_oauth_email');
              } else {
                console.error('Auth still failed after retry');
              }
            }
          } catch (verifyError) {
            console.error('Verify failed:', verifyError);
            // Fallback: try normal auth check
            const status = await auth.checkAuth();
            setAuthStatus(status);
            if (status.authenticated) {
              const userData = await auth.getCurrentUser();
              setUser(userData);
              sessionStorage.removeItem('centi_oauth_email');
            }
          }
        } else {
          // Check if we have backup email in sessionStorage (for mobile Safari cookie issues)
          const backupEmail = sessionStorage.getItem('centi_oauth_email');
          if (backupEmail) {
            console.log('Found backup email in sessionStorage, retrying verify...');
            try {
              const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
              await fetch(`${API_BASE_URL}/api/auth/verify?email=${encodeURIComponent(backupEmail)}`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                  'Content-Type': 'application/json',
                },
              });
              await new Promise(resolve => setTimeout(resolve, 500));
            } catch (e) {
              console.error('Backup verify failed:', e);
            }
          }
          
          // Normal auth check
          const status = await auth.checkAuth();
          setAuthStatus(status);
          
          if (status.authenticated) {
            const userData = await auth.getCurrentUser();
            setUser(userData);
            sessionStorage.removeItem('centi_oauth_email');
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


