import React, { useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import ChatInterface from './components/ChatInterface'
import QuestionGenerator from './components/QuestionGenerator'
import SummaryGenerator from './components/SummaryGenerator'
import Flashcards from './components/Flashcards'
import Dashboard from './components/Dashboard'
import Sidebar from './components/Sidebar'
import './App.css'

function App() {
  const [sessionId] = useState(() => uuidv4())
  const [activeView, setActiveView] = useState('chat')

  const renderView = () => {
    switch (activeView) {
      case 'chat':
        return <ChatInterface sessionId={sessionId} />
      case 'questions':
        return <div className="scrollable-view"><QuestionGenerator /></div>
      case 'summary':
        return <div className="scrollable-view"><SummaryGenerator /></div>
      case 'flashcards':
        return <div className="scrollable-view"><Flashcards /></div>
      case 'dashboard':
        return <div className="scrollable-view"><Dashboard /></div>
      default:
        return <ChatInterface sessionId={sessionId} />
    }
  }

  return (
    <div className="app">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />
      
      <main className="main-content">
        {renderView()}
      </main>
    </div>
  )
}

export default App
