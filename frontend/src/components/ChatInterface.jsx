import React, { useState, useRef, useEffect } from 'react'
import { FaPaperPlane, FaRobot, FaUser, FaBook, FaSpinner } from 'react-icons/fa'
import ReactMarkdown from 'react-markdown'
import { askQuestion } from '../utils/api'
import './ChatInterface.css'

function ChatInterface({ sessionId }) {
  const [messages, setMessages] = useState([
    {
      type: 'bot',
      content: 'Здравей! Аз съм твоят асистент по Information Retrieval. 📚\n\n' +
               'Задай ми въпрос **на български език** за учебния материал!\n\n' +
               '🇧🇬 Supported language: Bulgarian only',
      timestamp: new Date(),
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [retrievalMethod, setRetrievalMethod] = useState('hybrid')
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!inputValue.trim() || isLoading) return

    const userMessage = {
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await askQuestion(
        userMessage.content,
        sessionId,
        retrievalMethod
      )

      const botMessage = {
        type: 'bot',
        content: response.answer,
        sources: response.sources,
        chatId: response.chat_id,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, botMessage])
    } catch (error) {
      let errorContent = ''
      
      // Check if it's a language validation error
      if (error.response?.status === 400 && error.response?.data?.detail?.error === 'language_not_supported') {
        const detail = error.response.data.detail
        errorContent = `🌐 ${detail.message}\n\n` +
                      `Този чатбот отговаря **само на въпроси на български език** за материалите по Information Retrieval.\n\n` +
                      `Detected: ${detail.detected_language} | Supported: ${detail.supported_language}`
      } else if (error.response?.status === 400) {
        // Other validation errors
        errorContent = `⚠️ ${error.response?.data?.detail?.message || error.response?.data?.detail || 'Невалиден въпрос'}`
      } else {
        // General errors (Ollama connection, etc.)
        errorContent = '⚠️ Съжалявам, възникна грешка. Моля, уверете се че Ollama работи и опитайте отново.\n\n' + 
                       'Можете да стартирате Ollama с: `ollama serve`'
      }
      
      const errorMessage = {
        type: 'bot',
        content: errorContent,
        error: true,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="header-content">
          <FaRobot className="header-icon" />
          <div>
            <h2>Чат с IR Асистент</h2>
            <p className="header-subtitle">Задавай въпроси на български език 🇧🇬</p>
          </div>
        </div>
        
        <div className="retrieval-selector">
          <label>Метод:</label>
          <select 
            value={retrievalMethod} 
            onChange={(e) => setRetrievalMethod(e.target.value)}
            className="method-select"
          >
            <option value="hybrid">Hybrid (BM25 + Vector)</option>
            <option value="bm25">BM25 Only</option>
            <option value="vector">Vector Only</option>
          </select>
        </div>
      </div>

      <div className="messages-container">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message ${message.type} ${message.error ? 'error' : ''} fade-in`}
          >
            <div className="message-avatar">
              {message.type === 'bot' ? <FaRobot /> : <FaUser />}
            </div>
            
            <div className="message-content">
              <div className="message-header">
                <span className="message-sender">
                  {message.type === 'bot' ? 'IR Assistant' : 'Ти'}
                </span>
                <span className="message-time">
                  {message.timestamp.toLocaleTimeString('bg-BG', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              </div>
              
              <div className="message-text">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>

              {message.sources && message.sources.length > 0 && (
                <div className="message-sources">
                  <h4><FaBook /> Източници:</h4>
                  {message.sources.map((source, idx) => (
                    <div key={idx} className="source-item">
                      <div className="source-header">
                        <span className="source-page">Страница {source.page}</span>
                        <span className="source-score">Релевантност: {(source.score * 100).toFixed(0)}%</span>
                      </div>
                      <div className="source-section">{source.section_title}</div>
                      <div className="source-text">{source.text}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message bot loading fade-in">
            <div className="message-avatar">
              <FaRobot />
            </div>
            <div className="message-content">
              <div className="loading-indicator">
                <FaSpinner className="spinner" />
                <span>Търся в материалите и генерирам отговор...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Задай въпрос на български език..."
          className="chat-input"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="send-button"
          disabled={!inputValue.trim() || isLoading}
        >
          <FaPaperPlane />
        </button>
      </form>
    </div>
  )
}

export default ChatInterface
