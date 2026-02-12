import React from 'react'
import { FaComments, FaQuestionCircle, FaBook, FaFileAlt, FaLightbulb, FaChartBar } from 'react-icons/fa'
import './Sidebar.css'

function Sidebar({ activeView, setActiveView }) {
  const navItems = [
    { id: 'chat', icon: FaComments, label: 'Чат' },
    { id: 'questions', icon: FaQuestionCircle, label: 'Тестове' },
    { id: 'summary', icon: FaFileAlt, label: 'Резюмета' },
    { id: 'flashcards', icon: FaLightbulb, label: 'Флашкарти' },
    { id: 'dashboard', icon: FaChartBar, label: 'Табло' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <FaBook className="sidebar-logo" />
        <h1 className="sidebar-title">IR Assistant</h1>
        <p className="sidebar-subtitle">Information Retrieval</p>
      </div>
      
      <nav className="sidebar-nav">
        {navItems.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            className={`nav-item ${activeView === id ? 'active' : ''}`}
            onClick={() => setActiveView(id)}
          >
            <Icon />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      
      <div className="sidebar-footer">
        <p className="footer-text">© 2026 IR Assistant</p>
        <p className="footer-text small">Powered by Llama 3.1</p>
      </div>
    </aside>
  )
}

export default Sidebar
