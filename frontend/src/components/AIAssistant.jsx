/**
 * AIAssistant.jsx
 *
 * Right panel of the Log Interaction screen.
 *
 * Phase 5 additions:
 *   1. Spinner on "Log" button while isThinking is true.
 *   2. Input textarea disabled while thinking.
 *   3. Error handling — if POST /api/chat fails, an error message is shown
 *      in the chat history.
 *   4. WebSocket disconnect banner — shown when the WebSocket drops and
 *      auto-reconnect is in progress.
 *
 * CRITICAL: session_id is generated here and stored in a ref so handleSend
 * always uses the current value even before Redux has updated.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { addMessage, setThinking, setSessionId } from '../store/chatSlice';
import { connectWebSocket } from '../services/websocket';
import './AIAssistant.css';

const API_BASE_URL = 'http://localhost:8000';

// ─── Spinner SVG ─────────────────────────────────────────────────────────────
const Spinner = () => (
  <svg
    className="btn-spinner"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <circle
      cx="12"
      cy="12"
      r="9"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeDasharray="40 20"
    />
  </svg>
);

// ─── Component ────────────────────────────────────────────────────────────────
const AIAssistant = () => {
  const [inputValue, setInputValue]     = useState('');
  const [wsDisconnected, setWsDisconnected] = useState(false);

  const chat     = useSelector((state) => state.chat);
  const dispatch = useDispatch();

  // Stable refs — never stale inside callbacks
  const sessionIdRef = useRef(null);
  const wsRef        = useRef(null);
  const chatEndRef   = useRef(null);

  // ── WebSocket lifecycle ────────────────────────────────────────────────────
  useEffect(() => {
    const newSessionId = `session_${Date.now()}`;
    sessionIdRef.current = newSessionId;
    dispatch(setSessionId(newSessionId));

    console.log('[AIAssistant] Connecting WebSocket for session:', newSessionId);

    wsRef.current = connectWebSocket(newSessionId, dispatch, {
      onDisconnect: () => setWsDisconnected(true),
      onReconnect:  () => setWsDisconnected(false),
    });

    return () => {
      console.log('[AIAssistant] Unmounting — closing WebSocket intentionally');
      if (wsRef.current) wsRef.current.close();
    };
  }, [dispatch]); // runs exactly once on mount

  // ── Auto-scroll ────────────────────────────────────────────────────────────
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat.messages, chat.isThinking]);

  // ── Send message ───────────────────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const message = inputValue.trim();
    if (!message || chat.isThinking) return;

    const currentSessionId = sessionIdRef.current;
    if (!currentSessionId) {
      console.error('[AIAssistant] No session_id yet — WebSocket may not be ready');
      return;
    }

    console.log('[AIAssistant] Sending message for session:', currentSessionId, '→', message);

    // 1. Clear input immediately
    setInputValue('');

    // 2. Add user message to chat
    dispatch(
      addMessage({
        id:        Date.now(),
        role:      'user',
        content:   message,
        timestamp: new Date().toISOString(),
      })
    );

    // 3. Optimistically show thinking
    dispatch(setThinking(true));

    // 4. POST — AI response arrives via WebSocket
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ message, session_id: currentSessionId }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      console.log('[AIAssistant] POST /api/chat accepted — waiting for WebSocket response…');
    } catch (error) {
      console.error('[AIAssistant] ❌ Error sending message:', error);
      dispatch(setThinking(false));
      dispatch(
        addMessage({
          id:        Date.now(),
          role:      'assistant',
          content:   `⚠️ Sorry, I couldn't reach the server. Please make sure the backend is running on port 8000 and try again.\n\nError: ${error.message}`,
          timestamp: new Date().toISOString(),
          isError:   true,
        })
      );
    }
  }, [inputValue, chat.isThinking, dispatch]);

  // ── Keyboard shortcut ──────────────────────────────────────────────────────
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="ai-assistant-container">

      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-icon">🤖</div>
        <div>
          <h3>AI Assistant</h3>
          <span className="chat-header-subtitle">
            Describe your interaction and I'll log it for you
          </span>
        </div>
      </div>

      {/* WebSocket disconnect banner */}
      {wsDisconnected && (
        <div className="ws-disconnect-banner" role="alert">
          <span className="ws-banner-dot" />
          Reconnecting to server…
        </div>
      )}

      {/* Message history */}
      <div className="chat-history">
        {chat.messages.length === 0 && !chat.isThinking ? (
          <div className="empty-chat">
            <div className="empty-chat-icon">💬</div>
            <p className="empty-chat-title">Start by describing your interaction</p>
            <p className="empty-chat-hint">
              Try:{' '}
              <em>"Met Dr. Smith today, discussed OncoBoost efficacy, positive sentiment"</em>
            </p>
          </div>
        ) : (
          chat.messages.map((msg) => (
            <div
              key={msg.id}
              className={`chat-message ${msg.role}${msg.isError ? ' error-message' : ''}`}
            >
              <div className="message-bubble">
                <p className="message-content">{msg.content}</p>
                <span className="message-timestamp">
                  {new Date(msg.timestamp).toLocaleTimeString([], {
                    hour:   '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
            </div>
          ))
        )}

        {/* Animated three-dot thinking indicator */}
        {chat.isThinking && (
          <div className="chat-message assistant">
            <div className="message-bubble thinking-bubble">
              <span className="thinking-dot" />
              <span className="thinking-dot" />
              <span className="thinking-dot" />
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={chatEndRef} />
      </div>

      {/* Input area */}
      <div className="chat-input-container">
        <textarea
          id="ai-chat-input"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="E.g., Met Dr. Smith today, discussed OncoBoost efficacy…"
          rows={3}
          disabled={chat.isThinking}
          aria-label="Chat message input"
        />
        <button
          id="ai-chat-send-btn"
          onClick={handleSend}
          className={`log-button${chat.isThinking ? ' log-button--loading' : ''}`}
          disabled={chat.isThinking || !inputValue.trim()}
          aria-label={chat.isThinking ? 'Processing…' : 'Send message'}
        >
          {chat.isThinking ? (
            <>
              <Spinner />
              <span>Processing…</span>
            </>
          ) : (
            'Log'
          )}
        </button>
      </div>
    </div>
  );
};

export default AIAssistant;
