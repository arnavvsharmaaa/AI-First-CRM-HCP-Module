import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  messages: [],     // [{id, role:'user'|'assistant', content, timestamp}]
  isThinking: false,
  sessionId: null,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addMessage: (state, action) => {
      state.messages.push(action.payload);
    },
    setThinking: (state, action) => {
      state.isThinking = action.payload;
    },
    setSessionId: (state, action) => {
      state.sessionId = action.payload;
    },
    clearChat: (state) => {
      state.messages = [];
      state.isThinking = false;
    },
  },
});

export const { addMessage, setThinking, setSessionId, clearChat } = chatSlice.actions;

export default chatSlice.reducer;
