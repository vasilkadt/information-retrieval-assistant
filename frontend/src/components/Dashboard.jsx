import React, { useState, useEffect } from 'react'
import {
  FaChartBar, FaComments, FaQuestionCircle, FaDatabase,
  FaCheckCircle, FaTimesCircle, FaStar, FaSync, FaRobot,
  FaCogs, FaFire, FaClock, FaLayerGroup, FaSearch,
  FaTrophy, FaChartLine, FaBookOpen, FaBolt
} from 'react-icons/fa'
import { getStats, healthCheck } from '../utils/api'
import './Dashboard.css'

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uptime, setUptime] = useState(0)

  const loadData = async () => {
    setLoading(true)
    try {
      const [statsData, healthData] = await Promise.all([
        getStats(),
        healthCheck()
      ])
      setStats(statsData)
      setHealth(healthData)
    } catch (e) {
      console.error('Failed to load dashboard data:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    // Update uptime counter
    const interval = setInterval(() => setUptime(u => u + 1), 1000)
    return () => clearInterval(interval)
  }, [])

  const formatUptime = (seconds) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="dashboard-loading">
          <FaSync className="spin" />
          <p>Зареждане на статистики...</p>
        </div>
      </div>
    )
  }

  const services = health?.services || {}
  const totalInteractions = (stats?.total_chats || 0) + (stats?.total_generated_questions || 0)
  const healthyCount = Object.values(services).filter(Boolean).length
  const totalServices = Object.keys(services).length

  // Day names in Bulgarian
  const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']

  // Build 7-day activity chart data
  const activityData = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const dateStr = d.toISOString().split('T')[0]
    const dayEntry = stats?.daily_activity?.find(a => a.date === dateStr)
    activityData.push({
      day: dayNames[d.getDay() === 0 ? 6 : d.getDay() - 1],
      date: dateStr,
      count: dayEntry?.count || 0
    })
  }
  const maxActivity = Math.max(...activityData.map(d => d.count), 1)

  // Difficulty colors
  const difficultyColors = { easy: '#10b981', medium: '#f59e0b', hard: '#ef4444' }
  const difficultyLabels = { easy: 'Лесни', medium: 'Средни', hard: 'Трудни' }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-icon">
          <FaChartBar />
        </div>
        <div>
          <h2>Табло за Управление</h2>
          <p className="dashboard-subtitle">Статистики, активност и състояние на системата</p>
        </div>
        <button className="refresh-btn" onClick={loadData} title="Обнови">
          <FaSync />
        </button>
      </div>

      {/* Hero Stats */}
      <div className="hero-stats">
        <div className="hero-card total">
          <div className="hero-icon"><FaFire /></div>
          <div className="hero-content">
            <span className="hero-number">{totalInteractions}</span>
            <span className="hero-label">Общо взаимодействия</span>
          </div>
        </div>
        <div className="hero-card uptime">
          <div className="hero-icon"><FaClock /></div>
          <div className="hero-content">
            <span className="hero-number mono">{formatUptime(uptime)}</span>
            <span className="hero-label">Сесия</span>
          </div>
        </div>
        <div className="hero-card health-hero">
          <div className="hero-icon"><FaBolt /></div>
          <div className="hero-content">
            <span className="hero-number">{healthyCount}/{totalServices}</span>
            <span className="hero-label">Активни услуги</span>
          </div>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card chat-stat">
          <div className="stat-card-icon"><FaComments /></div>
          <div className="stat-card-content">
            <span className="stat-number">{stats?.total_chats || 0}</span>
            <span className="stat-label">Зададени въпроса</span>
          </div>
        </div>
        <div className="stat-card questions-stat">
          <div className="stat-card-icon"><FaQuestionCircle /></div>
          <div className="stat-card-content">
            <span className="stat-number">{stats?.total_generated_questions || 0}</span>
            <span className="stat-label">Генерирани въпроси</span>
          </div>
        </div>
        <div className="stat-card rating-stat">
          <div className="stat-card-icon"><FaStar /></div>
          <div className="stat-card-content">
            <span className="stat-number">{stats?.average_rating ?? '—'}</span>
            <span className="stat-label">Среден рейтинг</span>
          </div>
        </div>
        <div className="stat-card cache-stat">
          <div className="stat-card-icon"><FaDatabase /></div>
          <div className="stat-card-content">
            <span className="stat-number">{stats?.cached_questions || 0}</span>
            <span className="stat-label">Кеширани въпроси</span>
          </div>
        </div>
        <div className="stat-card feedback-stat">
          <div className="stat-card-icon"><FaTrophy /></div>
          <div className="stat-card-content">
            <span className="stat-number">{stats?.total_feedback || 0}</span>
            <span className="stat-label">Обратна връзка</span>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="charts-row">
        {/* Activity Chart */}
        <div className="chart-card wide">
          <h3 className="card-title"><FaChartLine /> Активност (последни 7 дни)</h3>
          <div className="activity-chart">
            {activityData.map((d, i) => (
              <div key={i} className="activity-col">
                <div className="activity-bar-container">
                  <div
                    className="activity-bar"
                    style={{ height: `${(d.count / maxActivity) * 100}%` }}
                  >
                    {d.count > 0 && <span className="bar-value">{d.count}</span>}
                  </div>
                </div>
                <span className="activity-day">{d.day}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Question Types Donut */}
        <div className="chart-card">
          <h3 className="card-title"><FaLayerGroup /> Типове въпроси</h3>
          {stats?.questions_by_type && Object.keys(stats.questions_by_type).length > 0 ? (
            <div className="donut-chart">
              {Object.entries(stats.questions_by_type).map(([type, count]) => {
                const total = stats.total_generated_questions || 1
                const pct = Math.round((count / total) * 100)
                const label = type === 'multiple_choice' ? 'Тестови' : 'Отворени'
                const color = type === 'multiple_choice' ? '#3b82f6' : '#8b5cf6'
                return (
                  <div key={type} className="donut-item">
                    <div className="donut-bar-row">
                      <div className="donut-color" style={{ background: color }} />
                      <span className="donut-label">{label}</span>
                      <span className="donut-value">{count}</span>
                    </div>
                    <div className="donut-bar-bg">
                      <div className="donut-bar-fill" style={{ width: `${pct}%`, background: color }} />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="empty-chart">
              <FaQuestionCircle />
              <p>Няма генерирани въпроси</p>
            </div>
          )}
        </div>
      </div>

      {/* Second Row */}
      <div className="charts-row">
        {/* Difficulty Distribution */}
        <div className="chart-card">
          <h3 className="card-title"><FaFire /> По трудност</h3>
          {stats?.questions_by_difficulty && Object.keys(stats.questions_by_difficulty).length > 0 ? (
            <div className="difficulty-chart">
              {Object.entries(stats.questions_by_difficulty).map(([diff, count]) => {
                const total = stats.total_generated_questions || 1
                const pct = Math.round((count / total) * 100)
                return (
                  <div key={diff} className="difficulty-item">
                    <div className="difficulty-header">
                      <span className="difficulty-dot" style={{ background: difficultyColors[diff] || '#94a3b8' }} />
                      <span className="difficulty-name">{difficultyLabels[diff] || diff}</span>
                      <span className="difficulty-count">{count} ({pct}%)</span>
                    </div>
                    <div className="difficulty-bar-bg">
                      <div className="difficulty-bar-fill" style={{ width: `${pct}%`, background: difficultyColors[diff] || '#94a3b8' }} />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="empty-chart">
              <FaFire />
              <p>Няма данни за трудност</p>
            </div>
          )}
        </div>

        {/* Retrieval Methods */}
        <div className="chart-card">
          <h3 className="card-title"><FaSearch /> Методи за търсене</h3>
          {stats?.retrieval_methods && Object.keys(stats.retrieval_methods).length > 0 ? (
            <div className="methods-chart">
              {Object.entries(stats.retrieval_methods).map(([method, count]) => {
                const total = stats.total_chats || 1
                const pct = Math.round((count / total) * 100)
                const methodColors = { hybrid: '#3b82f6', bm25: '#f59e0b', vector: '#10b981' }
                return (
                  <div key={method} className="method-item">
                    <div className="method-label">
                      <span className="method-dot" style={{ background: methodColors[method] || '#94a3b8' }} />
                      <span>{method.toUpperCase()}</span>
                      <span className="method-pct">{pct}%</span>
                    </div>
                    <div className="method-bar-bg">
                      <div className="method-bar-fill" style={{ width: `${pct}%`, background: methodColors[method] || '#94a3b8' }} />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="empty-chart">
              <FaSearch />
              <p>Няма данни за методи</p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity & Top Sections */}
      <div className="charts-row">
        {/* Recent Questions */}
        <div className="chart-card">
          <h3 className="card-title"><FaClock /> Последни въпроси</h3>
          {stats?.recent_questions?.length > 0 ? (
            <div className="recent-list">
              {stats.recent_questions.map((q, i) => (
                <div key={i} className="recent-item">
                  <div className="recent-icon"><FaComments /></div>
                  <div className="recent-content">
                    <p className="recent-question">{q.question}</p>
                    <span className="recent-time">{new Date(q.time).toLocaleString('bg-BG')}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-chart">
              <FaClock />
              <p>Няма зададени въпроси</p>
            </div>
          )}
        </div>

        {/* Top Sections */}
        <div className="chart-card">
          <h3 className="card-title"><FaBookOpen /> Популярни секции</h3>
          {stats?.top_sections?.length > 0 ? (
            <div className="sections-list">
              {stats.top_sections.map((s, i) => (
                <div key={i} className="section-row">
                  <span className="section-rank">#{i + 1}</span>
                  <span className="section-name">{s.section}</span>
                  <span className="section-count">{s.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-chart">
              <FaBookOpen />
              <p>Няма данни за секции</p>
            </div>
          )}
        </div>
      </div>

      {/* System Health */}
      <div className="health-section">
        <h3 className="card-title"><FaCogs /> Състояние на системата</h3>
        <div className="health-grid">
          {[
            { key: 'database', label: 'База Данни', icon: FaDatabase },
            { key: 'rag_pipeline', label: 'RAG Pipeline', icon: FaRobot },
            { key: 'question_generator', label: 'Генератор', icon: FaQuestionCircle },
          ].map(({ key, label, icon: Icon }) => (
            <div key={key} className={`health-item ${services[key] ? 'healthy' : 'unhealthy'}`}>
              <div className="health-status-dot" />
              <Icon className="health-svc-icon" />
              <div className="health-info">
                <span className="health-name">{label}</span>
                <span className="health-status-text">{services[key] ? 'Активен' : 'Неактивен'}</span>
              </div>
              {services[key] ? <FaCheckCircle className="health-check" /> : <FaTimesCircle className="health-cross" />}
            </div>
          ))}
        </div>
      </div>

      {/* Features Showcase */}
      <div className="features-section">
        <h3 className="card-title">🚀 Възможности на IR Assistant</h3>
        <div className="features-grid">
          {[
            { icon: '💬', name: 'Чат с AI', desc: 'RAG-базиран въпрос-отговор' },
            { icon: '📝', name: 'Тестове', desc: 'Генериране на тестови въпроси' },
            { icon: '📄', name: 'Резюмета', desc: 'Обобщения по всяка тема' },
            { icon: '🃏', name: 'Флашкарти', desc: 'Интерактивно учене' },
            { icon: '🇧🇬', name: 'Български', desc: 'Пълна поддръжка на БГ' },
            { icon: '⚡', name: 'Кеширане', desc: 'Бърз отговор при повторение' },
            { icon: '🔍', name: 'Хибридно търсене', desc: 'BM25 + Vector + Hybrid' },
            { icon: '📊', name: 'Статистики', desc: 'Подробно табло' },
          ].map((f, i) => (
            <div key={i} className="feature-card">
              <span className="feature-emoji">{f.icon}</span>
              <span className="feature-name">{f.name}</span>
              <span className="feature-desc">{f.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
