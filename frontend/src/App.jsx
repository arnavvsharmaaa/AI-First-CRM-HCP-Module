import React from 'react';
import LogInteractionScreen from './components/LogInteractionScreen';
import './App.css';

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>AI-First CRM HCP Module</h1>
      </header>
      <main className="app-main">
        <LogInteractionScreen />
      </main>
    </div>
  );
}

export default App;
