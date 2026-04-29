/**
 * websocket.js
 *
 * Manages the WebSocket connection between the React frontend and the
 * FastAPI backend at ws://localhost:8000/ws/{session_id}.
 *
 * WebSocket message types handled:
 *
 *   form_update  — payload shape from backend:
 *     {
 *       "type": "form_update",
 *       "fields": { "hcpName": "Dr. Patel", "sentiment": "neutral", ... },
 *       "ai_message": "Got it! I've logged your interaction.",
 *       "aiSuggestedFollowups": ["Follow up in 2 weeks", ...]
 *     }
 *     → dispatch updateFormFields({ ...data.fields, aiSuggestedFollowups: [...] })
 *     → dispatch addMessage (ai_message)
 *     → dispatch setThinking(false)
 *
 *   thinking  — payload: { "type": "thinking", "value": true|false }
 *     → dispatch setThinking(value)
 *
 * Auto-reconnect: Yes — 3 s delay after any unexpected disconnect.
 * Intentional close (component unmount): guarded by deliberate flag.
 *
 * Phase 5: accepts optional { onDisconnect, onReconnect } callbacks so the
 * AIAssistant can show/hide the "Reconnecting…" banner without coupling the
 * service layer to React state.
 */

import { updateFormFields } from '../store/interactionSlice';
import { setThinking, addMessage } from '../store/chatSlice';

const WS_BASE_URL       = 'ws://localhost:8000/ws';
const RECONNECT_DELAY_MS = 3000;

/**
 * Creates and manages a WebSocket connection for a given session.
 *
 * @param {string}   sessionId   Unique session identifier
 * @param {Function} dispatch    Redux dispatch function
 * @param {Object}   [callbacks] Optional lifecycle hooks
 * @param {Function} [callbacks.onDisconnect] Called when WS drops unexpectedly
 * @param {Function} [callbacks.onReconnect]  Called when WS reconnects
 * @returns {WebSocket} The managed WebSocket instance
 */
export const connectWebSocket = (sessionId, dispatch, callbacks = {}) => {
  const { onDisconnect, onReconnect } = callbacks;
  const wsUrl = `${WS_BASE_URL}/${sessionId}`;
  console.log('[WS] Connecting to:', wsUrl);

  let deliberate = false; // set true on intentional close → skip reconnect

  const ws = new WebSocket(wsUrl);

  // ── Open ──────────────────────────────────────────────────────────────────
  ws.onopen = () => {
    console.log('[WS] ✅ Connected →', wsUrl);
    // Signal successful (re)connection to the UI
    if (typeof onReconnect === 'function') onReconnect();
  };

  // ── Message ───────────────────────────────────────────────────────────────
  ws.onmessage = (event) => {
    console.log('[WS] 📨 Raw message received:', event.data);

    let data;
    try {
      data = JSON.parse(event.data);
    } catch (err) {
      console.error('[WS] ❌ Failed to parse message as JSON:', event.data, err);
      return;
    }

    console.log('[WS] Parsed message:', data);

    if (data.type === 'form_update') {
      // ── Build the complete fields object to merge into Redux ──────────────
      //
      // The backend sends:
      //   data.fields               → { hcpName, sentiment, topicsDiscussed, ... }
      //   data.aiSuggestedFollowups → ["...", "..."]  ← top-level, NOT inside fields
      //
      // Combine both into a single updateFormFields dispatch.
      const mergedFields = {
        ...(data.fields && typeof data.fields === 'object' ? data.fields : {}),
      };

      // Merge top-level aiSuggestedFollowups if present
      if (Array.isArray(data.aiSuggestedFollowups) && data.aiSuggestedFollowups.length > 0) {
        mergedFields.aiSuggestedFollowups = data.aiSuggestedFollowups;
      }

      console.log('[WS] Dispatching updateFormFields with:', mergedFields);

      if (Object.keys(mergedFields).length > 0) {
        dispatch(updateFormFields(mergedFields));
      }

      // Stop the thinking indicator
      dispatch(setThinking(false));

      // Add the AI's human-readable response to the chat
      if (data.ai_message && typeof data.ai_message === 'string' && data.ai_message.trim()) {
        console.log('[WS] Adding AI message to chat:', data.ai_message);
        dispatch(
          addMessage({
            id:        Date.now(),
            role:      'assistant',
            content:   data.ai_message,
            timestamp: new Date().toISOString(),
          })
        );
      }
    } else if (data.type === 'thinking') {
      console.log('[WS] Thinking indicator:', data.value);
      dispatch(setThinking(Boolean(data.value)));
    } else {
      console.warn('[WS] Unknown message type:', data.type, data);
    }
  };

  // ── Error ─────────────────────────────────────────────────────────────────
  ws.onerror = (error) => {
    console.error('[WS] ❌ Error:', error);
    // onclose fires next — handles reconnect
  };

  // ── Close / Reconnect ─────────────────────────────────────────────────────
  ws.onclose = (event) => {
    if (deliberate) {
      console.log('[WS] 🔌 Closed intentionally. Not reconnecting.');
      return;
    }
    console.warn(
      `[WS] 🔄 Disconnected (code ${event.code}). Reconnecting in ${RECONNECT_DELAY_MS / 1000}s…`
    );

    // Clear thinking indicator on unexpected disconnect
    dispatch(setThinking(false));

    // Notify the UI component so it can show the banner
    if (typeof onDisconnect === 'function') onDisconnect();

    setTimeout(() => {
      connectWebSocket(sessionId, dispatch, callbacks);
    }, RECONNECT_DELAY_MS);
  };

  // Wrap ws.close() so callers just call ws.close() and the guard is set automatically
  const originalClose = ws.close.bind(ws);
  ws.close = (code, reason) => {
    deliberate = true;
    originalClose(code, reason);
  };

  return ws;
};
