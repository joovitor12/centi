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
        const status = await auth.checkAuth();
        setAuthStatus(status);
        
        if (status.authenticated) {
          const userData = await auth.getCurrentUser();
          setUser(userData);
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

