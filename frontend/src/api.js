import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
});

// Attach token to every request if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const register = (username, password) =>
  api.post('/register', { username, password });

export const login = (username, password) =>
  api.post('/login', { username, password });

export const getHistory = () => api.get('/history');

export const getSessions = () => api.get('/sessions');

export const createSession = (title) => api.post('/sessions', { title });

export const getSessionMessages = (sessionId) =>
  api.get(`/sessions/${sessionId}/messages`);

export const updateSessionTitle = (sessionId, title) =>
  api.put(`/sessions/${sessionId}`, { title });

export const sendMessage = (message, sessionId) =>
  api.post('/chat', { message, session_id: sessionId });

export const getMe = () => api.get('/me');

export default api;