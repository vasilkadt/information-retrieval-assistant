import React from 'react'
import { FaComments, FaQuestionCircle, FaBook, FaChartBar } from 'react-icons/fa'
import './Sidebar.css'

function Sidebar({ activeView, setActiveView }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <FaBook className="sidebar-logo" />
        <h1 className="sidebar-title">IR Assistant</h1>
        <p className="sidebar-subtitle">Information Retrieval</p>
      </div>
      
      <nav className="sidebar-nav">
        <button
          className={`nav-item ${activeView === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveView('chat')}
        >
          <FaComments />
          <span>Чат</span>
        </button>
        
        <button
          className={`nav-item ${activeView === 'questions' ? 'active' : ''}`}
          onClick={() => setActiveView('questions')}
        >
          <FaQuestionCircle />
          <span>Тестови Въпроси</span>
        </button>
      </nav>
      
      <div className="sidebar-footer">
        <p className="footer-text">© 2026 IR Assistant</p>
        <p className="footer-text small">Powered by Llama 3.1</p>
      </div>
    </aside>
  )
}

export default Sidebar
