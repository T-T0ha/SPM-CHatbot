import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import {
  createSession,
  getSessionMessages,
  getSessions,
  sendMessage,
  updateSessionTitle,
} from '../api';
import '../App.css';

const Chat = ({ onLogout }) => {
  const { username: urlUsername } = useParams();
  const navigate = useNavigate();
  const storedUsername = localStorage.getItem('username');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const editInputRef = useRef(null);

  useEffect(() => {
    if (storedUsername && urlUsername !== storedUsername) {
      navigate(`/${storedUsername}`, { replace: true });
    }
  }, [urlUsername, storedUsername, navigate]);

  const startEditing = (sessionId, currentTitle) => {
    setEditingSessionId(sessionId);
    setEditTitle(currentTitle);
    setTimeout(() => editInputRef.current?.focus(), 0);
  };

  const saveTitle = async () => {
    const id = editingSessionId;
    if (!id) return;
    const newTitle = editTitle.trim() || 'New conversation';
    try {
      await updateSessionTitle(id, newTitle);
      setSessions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, title: newTitle } : s))
      );
    } catch (err) {
      console.error('Failed to update title', err);
    }
    setEditingSessionId(null);
    setEditTitle('');
  };

  const cancelEditing = () => {
    setEditingSessionId(null);
    setEditTitle('');
  };

  const loadSessions = async () => {
    try {
      const response = await getSessions();
      const fetchedSessions = response.data || [];
      setSessions(fetchedSessions);
      if (fetchedSessions.length > 0) {
        setActiveSessionId((prev) => prev ?? fetchedSessions[0].id);
      }
    } catch (err) {
      console.error('Failed to load sessions', err);
    } finally {
      setLoadingSessions(false);
    }
  };

  const loadMessages = async (sessionId) => {
    if (!sessionId) return;
    try {
      const response = await getSessionMessages(sessionId);
      setMessages(response.data);
    } catch (err) {
      console.error('Failed to load messages', err);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
    }
  }, [activeSessionId]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    const userMessage = input;
    setInput('');
    setLoading(true);

    const optimisticMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    try {
      let sessionId = activeSessionId;
      if (!sessionId) {
        const created = await createSession(userMessage.slice(0, 40));
        sessionId = created.data.id;
        setActiveSessionId(sessionId);
        setSessions((prev) => [created.data, ...prev]);
      }
      await sendMessage(userMessage, sessionId);
      await loadMessages(sessionId);
      await loadSessions();
    } catch (err) {
      console.error('Send failed', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = async () => {
    try {
      const created = await createSession('New conversation');
      setSessions((prev) => [created.data, ...prev]);
      setActiveSessionId(created.data.id);
      setMessages([]);
    } catch (err) {
      console.error('Failed to create session', err);
    }
  };

  const logout = () => {
    onLogout();
    navigate('/', { replace: true });
  };

  const sessionItems = useMemo(() => {
    return sessions.map((session) => ({
      id: session.id,
      title: session.title,
      time: session.last_message_at
        ? new Date(session.last_message_at).toLocaleTimeString()
        : 'No messages yet',
      count: session.message_count ?? 0,
    }));
  }, [sessions]);

  const activeSession = sessions.find((session) => session.id === activeSessionId);

  return (
    <div className="app-shell">
      <div className="chat-layout">
        <aside className="chat-sidebar">
          <div className="sidebar-header">
            <div className="sidebar-title">Conversations</div>
            <div className="sidebar-subtitle">Pick a session to continue.</div>
          </div>
          <button className="sidebar-action" type="button" onClick={handleNewSession}>
            New conversation
            <span>+</span>
          </button>
          <div className="sidebar-list">
            {!loadingSessions && sessionItems.length === 0 && (
              <div className="sidebar-item">
                <div className="sidebar-item-title">No conversations yet</div>
                <div className="sidebar-item-meta">Create one to get started.</div>
              </div>
            )}
            {sessionItems.map((item) => (
              <button
                key={item.id}
                className={`sidebar-item ${item.id === activeSessionId ? 'active' : ''}`}
                type="button"
                onClick={() => {
                  if (editingSessionId !== item.id) {
                    setActiveSessionId(item.id);
                  }
                }}
                onDoubleClick={() => startEditing(item.id, item.title)}
              >
                {editingSessionId === item.id && editingSessionId !== activeSessionId ? (
                  <input
                    ref={editInputRef}
                    className="sidebar-item-edit-input"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={saveTitle}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') saveTitle();
                      if (e.key === 'Escape') cancelEditing();
                    }}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <div className="sidebar-item-title">{item.title}</div>
                )}
                <div className="sidebar-item-meta">{item.time} · {item.count} msgs</div>
              </button>
            ))}
          </div>
        </aside>

        <div className="chat-panel">
          <div className="chat-header">
            <div className="brand">
              <h1>SPM Chat</h1>
              {activeSession && editingSessionId === activeSession.id ? (
                <input
                  className="header-edit-input"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onBlur={saveTitle}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') saveTitle();
                    if (e.key === 'Escape') cancelEditing();
                  }}
                  autoFocus
                />
              ) : (
                <span
                  onDoubleClick={() => activeSession && startEditing(activeSession.id, activeSession.title)}
                >
                  {activeSession ? activeSession.title : 'Start a new conversation'}
                </span>
              )}
            </div>
            <div className="header-actions">
              <span className="user-badge">{urlUsername}</span>
              <button onClick={logout} className="logout-button">Logout</button>
            </div>
          </div>
          <div className="messages-area">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`message ${msg.role === 'user' ? 'message-user' : 'message-assistant'}`}
              >
                <div className="message-role">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
                <div className="message-content">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                      {msg.content}
                    </ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>
                <div className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}
            {loading && <div className="typing-indicator">Assistant is typing...</div>}
          </div>
          <form onSubmit={handleSend} className="chat-input-form">
            <input
              type="text"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button type="submit" disabled={loading}>Send</button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Chat;