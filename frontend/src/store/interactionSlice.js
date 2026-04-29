/**
 * interactionSlice.js
 *
 * Redux slice for the LEFT panel form data (read-only from the UI).
 * All field updates arrive via WebSocket → updateFormFields reducer.
 *
 * NOTE: isThinking / setThinking live in chatSlice — NOT here.
 *       The setThinking export below is a backward-compat alias only.
 */

import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  id: null,
  hcpName: '',
  interactionType: 'Meeting',
  date: '',                    // 'YYYY-MM-DD'
  time: '',                    // 'HH:MM'
  attendees: [],
  topicsDiscussed: '',
  materialsShared: [],         // [{name, type}]
  samplesDistributed: [],      // [{product, quantity}]
  sentiment: 'neutral',        // 'positive' | 'neutral' | 'negative'
  outcomes: '',
  followUpActions: '',
  aiSuggestedFollowups: [],
  isLoading: false,
  lastUpdatedField: null,
};

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    /**
     * Update a single named field.
     * payload: { field: string, value: any }
     */
    updateInteractionField: (state, action) => {
      const { field, value } = action.payload;
      if (Object.prototype.hasOwnProperty.call(initialState, field)) {
        state[field] = value;
        state.lastUpdatedField = field;
      } else {
        console.warn('[interactionSlice] updateInteractionField: unknown field', field);
      }
    },

    /**
     * Update multiple fields at once (legacy helper).
     * payload: { fields: { [fieldName]: value } }
     */
    updateMultipleFields: (state, action) => {
      const { fields } = action.payload;
      if (!fields || typeof fields !== 'object') return;
      Object.entries(fields).forEach(([key, value]) => {
        if (Object.prototype.hasOwnProperty.call(initialState, key)) {
          state[key] = value;
        }
      });
      const keys = Object.keys(fields);
      state.lastUpdatedField = keys.length > 0 ? keys[0] : null;
    },

    /**
     * PRIMARY REDUCER — called by websocket.js on every form_update.
     *
     * Merges a flat object of partial field updates into the current state.
     * Only keys that exist in initialState are applied (safe merge).
     *
     * payload: { hcpName: "Dr. Patel", sentiment: "neutral", ... }
     *          (flat object — not nested under a "fields" key)
     */
    updateFormFields: (state, action) => {
      const incoming = action.payload;

      if (!incoming || typeof incoming !== 'object' || Array.isArray(incoming)) {
        console.warn('[interactionSlice] updateFormFields received invalid payload:', incoming);
        return;
      }

      console.log('[interactionSlice] updateFormFields received:', incoming);

      let firstKey = null;
      Object.entries(incoming).forEach(([key, value]) => {
        if (Object.prototype.hasOwnProperty.call(initialState, key)) {
          state[key] = value;
          if (!firstKey) firstKey = key;
        } else {
          // Don't error — backend may send extra keys like interaction_id
          console.log('[interactionSlice] Skipping unknown key:', key);
        }
      });

      state.lastUpdatedField = firstKey;
      console.log('[interactionSlice] State after updateFormFields — hcpName:', state.hcpName);
    },

    /**
     * Set the isLoading flag for long-running operations.
     */
    setLoading: (state, action) => {
      state.isLoading = Boolean(action.payload);
    },

    /**
     * Reset the form to its initial empty state.
     */
    resetInteraction: () => initialState,

    /**
     * Backward-compat alias — real thinking indicator lives in chatSlice.
     * This sets isLoading (the form spinner), not the chat thinking indicator.
     */
    setThinking: (state, action) => {
      state.isLoading = Boolean(action.payload);
    },
  },
});

export const {
  updateInteractionField,
  updateMultipleFields,
  updateFormFields,
  setLoading,
  resetInteraction,
  setThinking,
} = interactionSlice.actions;

export default interactionSlice.reducer;
