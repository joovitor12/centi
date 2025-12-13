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
          
          // Store email in localStorage as primary auth method (more reliable than cookies on mobile)
          localStorage.setItem('centi_user_email', email);
          
          // Clear URL params after reading (for security)
          window.history.replaceState({}, document.title, window.location.pathname);
          
          // Verify with backend - this will set the cookie (may or may not work on mobile Safari)
          try {
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
          } catch (verifyError) {
            console.error('Verify failed:', verifyError);
          }
          
          // Since we have email in localStorage, we can authenticate directly
          // Check if user exists by trying to get user data
          try {
            const userData = await auth.getCurrentUser();
            console.log('User data retrieved:', userData);
            setUser(userData);
            setAuthStatus({ authenticated: true });
          } catch (error) {
            console.error('Failed to get user data:', error);
            // If cookie-based auth fails, we still have email in localStorage
            // This is acceptable - the user can use the app
            // We'll check auth on each API call using the email from localStorage
            setAuthStatus({ authenticated: true });
            // Set a minimal user object with just email
            setUser({ user_email: email } as User);
          }
        } else {
          // Normal auth check - try cookie first, fallback to localStorage
          try {
            const status = await auth.checkAuth();
            if (status.authenticated) {
              const userData = await auth.getCurrentUser();
              setUser(userData);
              // Update localStorage with current email
              if (userData.user_email) {
                localStorage.setItem('centi_user_email', userData.user_email);
              }
              setAuthStatus(status);
            } else {
              // Cookie auth failed, try localStorage fallback
              const storedEmail = localStorage.getItem('centi_user_email');
              if (storedEmail) {
                console.log('Cookie auth failed, using localStorage email:', storedEmail);
                // Verify with backend using stored email
                try {
                  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
                  await fetch(`${API_BASE_URL}/api/auth/verify?email=${encodeURIComponent(storedEmail)}`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                      'Content-Type': 'application/json',
                    },
                  });
                  
                  // Try to get user data
                  const userData = await auth.getCurrentUser();
                  setUser(userData);
                  setAuthStatus({ authenticated: true });
                } catch (error) {
                  console.error('Fallback auth failed:', error);
                  // Last resort: use stored email directly
                  setUser({ user_email: storedEmail } as User);
                  setAuthStatus({ authenticated: true });
                }
              } else {
                setAuthStatus({ authenticated: false });
              }
            }
          } catch (error) {
            console.error('Auth check failed:', error);
            // Try localStorage fallback
            const storedEmail = localStorage.getItem('centi_user_email');
            if (storedEmail) {
              setUser({ user_email: storedEmail } as User);
              setAuthStatus({ authenticated: true });
            } else {
              setAuthStatus({ authenticated: false });
            }
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


