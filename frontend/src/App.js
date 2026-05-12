import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Auth from './components/auth';
import Chat from './components/chat';
import './App.css';

function App() {
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [username, setUsername] = useState(localStorage.getItem('username'));

  useEffect(() => {
    const handleStorage = () => {
      setToken(localStorage.getItem('access_token'));
      setUsername(localStorage.getItem('username'));
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const handleLogin = (newToken, newUsername) => {
    localStorage.setItem('access_token', newToken);
    localStorage.setItem('username', newUsername);
    setToken(newToken);
    setUsername(newUsername);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    setToken(null);
    setUsername(null);
  };

  if (!token) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/:username" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Auth onLogin={handleLogin} />} />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to={`/${username}`} replace />} />
        <Route path="/:username" element={<Chat onLogout={handleLogout} />} />
        <Route path="*" element={<Navigate to={`/${username}`} replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
