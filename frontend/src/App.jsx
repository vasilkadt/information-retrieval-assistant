import React, { useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import ChatInterface from './components/ChatInterface'
import QuestionGenerator from './components/QuestionGenerator'
import Sidebar from './components/Sidebar'
import './App.css'

function App() {
  const [sessionId] = useState(() => uuidv4())
  const [activeView, setActiveView] = useState('chat') // 'chat' or 'questions'

  return (
    <div className="app">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />
      
      <main className="main-content">
        {activeView === 'chat' ? (
          <ChatInterface sessionId={sessionId} />
        ) : (
          <QuestionGenerator />
        )}
      </main>
    </div>
  )
}

export default App
