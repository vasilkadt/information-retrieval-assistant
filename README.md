# information-retrieval-assistant

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## Data Processing

Документът IR_lecture_notes.pdf се обработва чрез собствен pipeline:

1. Extract текст по страници (PyMuPDF)
2. Почистване на шум и счупени думи
3. Детекция на секции по номерирани заглавия
4. Chunking с overlap
5. Индексиране с BM25

Pipeline-ът е имплементиран в папка /scripts.
За удобство обработените файлове са включени директно в проекта.

### Scripts

1) 01_extract_pages.py – PDF → текст по страници
2) 02_clean_pages.py – чисти шума от текста
3) 03_detect_sections.py – открива секции/заглавия
4) 04_chunk.py – разбива текста на малки пасажи (chunks)
5) 05_build_bm25.py – прави индекс за търсене (BM25)
6) 99_retrieval_smoke_test.py – проверка дали търсенето работи

```bash
python 01_extract_pages.py
```

### Файлове

- pages.jsonl – суров текст по страници
- pages_clean.jsonl – почистен текст
- pages_with_sections.jsonl – текст + секции
- chunks.jsonl – основната база знания (ползва се от системата)
- bm25_index.pkl – индексът за търсене (IR ядрото)
