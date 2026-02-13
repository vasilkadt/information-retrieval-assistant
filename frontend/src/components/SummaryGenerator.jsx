import React, { useState, useEffect } from 'react'
import { FaFileAlt, FaSpinner, FaBookOpen, FaListUl, FaSearch } from 'react-icons/fa'
import ReactMarkdown from 'react-markdown'
import { summarizeTopic, getTopics } from '../utils/api'
import './SummaryGenerator.css'

function SummaryGenerator() {
  const [topic, setTopic] = useState('')
  const [detailLevel, setDetailLevel] = useState('medium')
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [topics, setTopics] = useState([])
  const [showTopics, setShowTopics] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadTopics = async () => {
      try {
        const data = await getTopics()
        setTopics(data.topics || [])
      } catch (e) {
        console.error('Failed to load topics:', e)
      }
    }
    loadTopics()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!topic.trim()) return

    setLoading(true)
    setError(null)
    setSummary(null)

    try {
      const result = await summarizeTopic(topic, detailLevel)
      setSummary(result)
    } catch (e) {
      setError(e.response?.data?.detail || 'Грешка при генериране на резюме')
    } finally {
      setLoading(false)
    }
  }

  const selectTopic = (t) => {
    setTopic(t.title)
    setShowTopics(false)
  }

  const detailLevels = [
    { value: 'brief', label: '📌 Кратко', desc: '2-3 изречения' },
    { value: 'medium', label: '📝 Средно', desc: '5-7 изречения' },
    { value: 'detailed', label: '📖 Подробно', desc: '10-15 изречения' },
  ]

  return (
    <div className="summary-container">
      <div className="summary-header">
        <div className="summary-header-icon">
          <FaFileAlt />
        </div>
        <div>
          <h2>Резюмета на Теми</h2>
          <p className="summary-subtitle">Генерирай кратко резюме на всяка тема от учебния материал</p>
        </div>
      </div>

      <form className="summary-form" onSubmit={handleSubmit}>
        <div className="topic-input-group">
          <div className="topic-input-wrapper">
            <FaSearch className="input-icon" />
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Въведи тема (напр. BM25, Индексиране, TF-IDF...)"
              className="topic-input"
            />
            <button
              type="button"
              className="topics-toggle"
              onClick={() => setShowTopics(!showTopics)}
              title="Виж налични теми"
            >
              <FaListUl />
            </button>
          </div>

          {showTopics && (
            <div className="topics-dropdown">
              <div className="topics-dropdown-header">
                <FaBookOpen /> Налични теми от материала
              </div>
              <div className="topics-list">
                {topics.map((t, i) => (
                  <button key={i} className="topic-item" onClick={() => selectTopic(t)}>
                    <span className="topic-title">{t.title}</span>
                    <span className="topic-meta">Стр. {t.page} · {t.chunks} части</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="detail-level-group">
          <label className="detail-label">Ниво на детайлност:</label>
          <div className="detail-options">
            {detailLevels.map((level) => (
              <button
                key={level.value}
                type="button"
                className={`detail-option ${detailLevel === level.value ? 'active' : ''}`}
                onClick={() => setDetailLevel(level.value)}
              >
                <span className="detail-option-label">{level.label}</span>
                <span className="detail-option-desc">{level.desc}</span>
              </button>
            ))}
          </div>
        </div>

        <button type="submit" className="generate-btn" disabled={loading || !topic.trim()}>
          {loading ? (
            <>
              <FaSpinner className="spin" /> Генериране...
            </>
          ) : (
            <>
              <FaFileAlt /> Генерирай Резюме
            </>
          )}
        </button>
      </form>

      {error && (
        <div className="summary-error">
          ⚠️ {error}
        </div>
      )}

      {summary && (
        <div className="summary-result fade-in">
          <div className="summary-result-header">
            <h3>📄 Резюме: {summary.topic}</h3>
            <span className="detail-badge">{detailLevels.find(d => d.value === summary.detail_level)?.label}</span>
          </div>
          
          <div className="summary-content">
            <ReactMarkdown>{summary.summary}</ReactMarkdown>
          </div>

          <div className="summary-meta">
            <div className="meta-item">
              <span className="meta-label">📚 Източници:</span>
              <span className="meta-value">{summary.num_sources} части</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">📄 Страници:</span>
              <span className="meta-value">{summary.pages?.join(', ')}</span>
            </div>
            {summary.sections?.length > 0 && (
              <div className="meta-item full-width">
                <span className="meta-label">📑 Секции:</span>
                <div className="meta-tags">
                  {summary.sections.map((s, i) => (
                    <span key={i} className="section-tag">{s}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default SummaryGenerator
