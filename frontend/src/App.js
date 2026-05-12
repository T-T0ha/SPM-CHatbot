import React, { useState, useEffect } from 'react';
import Auth from './components/auth';
import Chat from './components/chat';
import './App.css';

function App() {
  const [token, setToken] = useState(localStorage.getItem('access_token'));

  useEffect(() => {
    const handleStorage = () => setToken(localStorage.getItem('access_token'));
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  if (!token) {
    return <Auth onLogin={(newToken) => setToken(newToken)} />;
  }
  return <Chat />;
}

export default App;