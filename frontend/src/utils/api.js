import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Question answering
export const askQuestion = async (question, sessionId, retrievalMethod = 'hybrid', model = 'llama3.1:8b') => {
  const response = await api.post('/ask', {
    question,
    session_id: sessionId,
    retrieval_method: retrievalMethod,
    model,
  })
  return response.data
}

// Search only (no generation)
export const searchChunks = async (query, method = 'hybrid', k = 5) => {
  const response = await api.get('/search', {
    params: { q: query, method, k },
  })
  return response.data
}

// Generate test questions
export const generateQuestions = async (questionType, numQuestions, section = null, difficulty = 'medium') => {
  const response = await api.post('/generate-questions', {
    question_type: questionType,
    num_questions: numQuestions,
    section,
    difficulty,
  })
  return response.data
}

// Get generated questions
export const getQuestions = async (type = null, limit = 50) => {
  const response = await api.get('/questions', {
    params: { type, limit },
  })
  return response.data
}

// Get chat history
export const getHistory = async (sessionId = null, limit = 50) => {
  const response = await api.get('/history', {
    params: { session_id: sessionId, limit },
  })
  return response.data
}

// Submit feedback
export const submitFeedback = async (chatId, rating, comment = null) => {
  const response = await api.post('/feedback', {
    chat_id: chatId,
    rating,
    comment,
  })
  return response.data
}

// Get statistics
export const getStats = async () => {
  const response = await api.get('/stats')
  return response.data
}

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}

export default api
