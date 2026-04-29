import React from 'react';
import InteractionForm from './InteractionForm';
import AIAssistant from './AIAssistant';
import './LogInteractionScreen.css';

const LogInteractionScreen = () => {
  return (
    <div className="log-interaction-screen">
      <div className="left-panel">
        <InteractionForm />
      </div>
      <div className="right-panel">
        <AIAssistant />
      </div>
    </div>
  );
};

export default LogInteractionScreen;
