import React, { useState } from 'react'
import { FaQuestionCircle, FaSpinner, FaCheckCircle, FaLightbulb } from 'react-icons/fa'
import { generateQuestions } from '../utils/api'
import './QuestionGenerator.css'

function QuestionGenerator() {
  const [questionType, setQuestionType] = useState('multiple_choice')
  const [numQuestions, setNumQuestions] = useState(5)
  const [difficulty, setDifficulty] = useState('medium')
  const [generatedQuestions, setGeneratedQuestions] = useState([])
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerate = async () => {
    setIsGenerating(true)
    setGeneratedQuestions([])

    try {
      const response = await generateQuestions(
        questionType,
        numQuestions,
        null,
        difficulty
      )
      setGeneratedQuestions(response.questions)
    } catch (error) {
      console.error('Error generating questions:', error)
      alert('Грешка при генериране на въпроси. Моля, уверете се че Ollama работи.')
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="question-generator">
      <div className="generator-header">
        <div className="header-content">
          <FaQuestionCircle className="header-icon" />
          <div>
            <h2>Генератор на Тестови Въпроси</h2>
            <p className="header-subtitle">Автоматично създаване на въпроси от учебния материал</p>
          </div>
        </div>
      </div>

      <div className="generator-content">
        <div className="settings-panel">
          <h3>Настройки</h3>
          
          <div className="setting-group">
            <label>Тип въпроси</label>
            <select
              value={questionType}
              onChange={(e) => setQuestionType(e.target.value)}
              className="setting-select"
            >
              <option value="multiple_choice">Multiple Choice (Затворени)</option>
              <option value="open_ended">Open-Ended (Отворени)</option>
            </select>
          </div>

          <div className="setting-group">
            <label>Брой въпроси</label>
            <input
              type="number"
              min="1"
              max="20"
              value={numQuestions}
              onChange={(e) => setNumQuestions(parseInt(e.target.value))}
              className="setting-input"
            />
          </div>

          <div className="setting-group">
            <label>Трудност</label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="setting-select"
            >
              <option value="easy">Лесни</option>
              <option value="medium">Средни</option>
              <option value="hard">Трудни</option>
            </select>
          </div>

          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="generate-button"
          >
            {isGenerating ? (
              <>
                <FaSpinner className="spinner" />
                Генериране...
              </>
            ) : (
              <>
                <FaLightbulb />
                Генерирай Въпроси
              </>
            )}
          </button>
        </div>

        <div className="questions-display">
          {generatedQuestions.length === 0 && !isGenerating && (
            <div className="empty-state">
              <FaQuestionCircle className="empty-icon" />
              <p>Няма генерирани въпроси</p>
              <p className="empty-hint">Изберете настройки и натиснете "Генерирай Въпроси"</p>
            </div>
          )}

          {isGenerating && (
            <div className="loading-state">
              <FaSpinner className="spinner large" />
              <p>Генериране на въпроси...</p>
              <p className="loading-hint">Това може да отнеме няколко минути</p>
            </div>
          )}

          {generatedQuestions.map((question, index) => (
            <div key={index} className="question-card fade-in">
              <div className="question-header">
                <span className="question-number">Въпрос {index + 1}</span>
                <span className="question-meta">
                  Стр. {question.page} • {question.section}
                </span>
              </div>

              <div className="question-text">{question.question}</div>

              {question.type === 'multiple_choice' && (
                <div className="options-list">
                  {question.options.map((option, optIndex) => (
                    <div
                      key={optIndex}
                      className={`option ${optIndex === question.correct_answer ? 'correct' : ''}`}
                    >
                      <span className="option-label">{String.fromCharCode(65 + optIndex)}.</span>
                      <span className="option-text">{option}</span>
                      {optIndex === question.correct_answer && (
                        <FaCheckCircle className="correct-icon" />
                      )}
                    </div>
                  ))}
                  
                  {question.explanation && (
                    <div className="explanation">
                      <strong>Обяснение:</strong> {question.explanation}
                    </div>
                  )}

                  {question.difficulty && (
                    <div className="difficulty-badge">
                      Трудност: {
                        question.difficulty === 'easy' ? 'Лесна' :
                        question.difficulty === 'medium' ? 'Средна' :
                        'Трудна'
                      }
                    </div>
                  )}
                </div>
              )}

              {question.type === 'open_ended' && (
                <div className="open-question-details">
                  <div className="key-points">
                    <h4>Ключови точки за отговор:</h4>
                    <ul>
                      {question.key_points.map((point, pointIndex) => (
                        <li key={pointIndex}>{point}</li>
                      ))}
                    </ul>
                  </div>

                  {question.sample_answer && (
                    <div className="sample-answer">
                      <h4>Примерен отговор:</h4>
                      <p>{question.sample_answer}</p>
                    </div>
                  )}

                  {question.difficulty && (
                    <div className="difficulty-badge">
                      Трудност: {
                        question.difficulty === 'easy' ? 'Лесен' :
                        question.difficulty === 'medium' ? 'Среден' :
                        'Труден'
                      }
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default QuestionGenerator
