# 🤖 Information Retrieval Assistant

Интелигентен чатбот асистент за отговаряне на въпроси по учебния материал за Information Retrieval, базиран на RAG (Retrieval-Augmented Generation) архитектура.

## ✨ Възможности

- **Интелигентно отговаряне на въпроси** - RAG pipeline с Ollama/Llama 3.1
- **Хибридно търсене** - Комбинация от BM25 и Vector Search
- **Препратки към източници** - Всеки отговор включва страници и секции
- **Генериране на тестови въпроси** - Автоматично създаване на въпроси с различна трудност
- **Поддръжка на български език** - Автоматична валидация на езика
- **Модерен UI** - React интерфейс с отлична UX
- **История на разговорите** - SQLite база данни

## 🏗️ Архитектура

```
React UI → FastAPI Backend → Retrieval (BM25 + Vector) + Ollama/Llama 3.1
```

**Технологии:**
- **Backend:** FastAPI, Sentence-Transformers, FAISS, Ollama, SQLite
- **Frontend:** React 18, Vite
- **LLM:** Llama 3.1 8B (локален модел)

## 🚀 Бърз Старт

### 1. Предварителни изисквания

- Python 3.9+
- Node.js 18+
- Ollama ([инсталирай от ollama.com](https://ollama.com))

### 2. Инсталация

```bash
# Клонирай проекта
git clone <repository-url>
cd information-retrieval-assistant

# Създай виртуална среда
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Инсталирай dependencies
pip install -r requirements.txt
```

### 3. Настройка на Ollama

```bash
# Стартирай Ollama (в отделен терминал)
ollama serve

# Изтегли Llama модела
ollama pull llama3.1:8b
```

### 4. Обработка на данни

```bash
cd scripts

# Последователно изпълни скриптовете
python 01_extract_pages.py    # Извлича текст от PDF
python 02_clean_pages.py      # Почиства текста
python 03_detect_sections.py  # Детектира секции
python 04_chunk.py            # Създава chunks
python 05_build_bm25.py       # Генерира BM25 индекс
python 06_build_embeddings.py # Генерира embeddings (10-30 мин)
```

### 5. Стартиране

**Backend:**
```bash
cd backend
python server.py
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

**Frontend (нов терминал):**
```bash
cd frontend
npm install
npm run dev
# UI: http://localhost:3000
```

## 🎯 Използване

### Чат Интерфейс

1. Отвори `http://localhost:3000`
2. Задай въпрос на български
3. Избери метод на търсене (Hybrid препоръчан)
4. Получи отговор с препратки към източници

**Примери:**
- "Какво е обърнат индекс?"
- "Обясни TF-IDF"
- "Как работи BM25?"

### Генериране на Въпроси

1. Отиди в "Тестови Въпроси"
2. Избери тип (Multiple Choice / Open-Ended)
3. Избери трудност (Лесни / Средни / Трудни)
4. Генерирай въпроси

## 🔧 API Endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/ask` | POST | Задай въпрос (RAG) |
| `/search` | GET | Търси в материалите |
| `/generate-questions` | POST | Генерирай тестови въпроси |
| `/questions` | GET | Вземи генерирани въпроси |
| `/history` | GET | История на разговорите |
| `/feedback` | POST | Изпрати feedback |
| `/health` | GET | Health check |

Пълна документация: `http://localhost:8000/docs`

## ⚙️ Конфигурация

### Промяна на LLM модела

В `backend/rag.py` и `backend/question_generator.py`:
```python
model_name = "llama3.1:3b"  # По-бърз, по-малък
model_name = "llama3.1:8b"  # Балансиран (по подразбиране)
```

### Retrieval методи

- `hybrid` - BM25 + Vector (препоръчано)
- `bm25` - Само keyword търсене (по-бързо)
- `vector` - Само semantic търсене

### Chunking параметри

В `scripts/04_chunk.py`:
```python
CHUNK_SIZE = 1200  # Размер на chunk (символи)
OVERLAP = 200      # Overlap между chunks
```

## 📋 Структура

```
├── data/
│   ├── raw/              # PDF файл
│   ├── processed/        # Обработени данни
│   └── index/            # BM25 и FAISS индекси
├── scripts/              # Скриптове за обработка
├── backend/              # FastAPI сървър
└── frontend/             # React приложение
```

## 🐛 Troubleshooting

**Ollama не работи:**
```bash
# Провери дали Ollama е стартиран
ollama serve

# Провери дали моделът е изтеглен
ollama list
```

**Embeddings отнемат много време:**
- Нормално е за първи път (10-30 мин)
- Използвай по-малък модел: `llama3.1:3b`

**Backend връща грешка:**
- Провери дали всички скриптове са изпълнени
- Провери дали индексите са генерирани (`data/index/`)

## 📄 License

MIT License

---

**Разработен за курса по Information Retrieval @ FMI**