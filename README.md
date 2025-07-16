# Zotero Knowledge Base

System do tworzenia bazy wiedzy z biblioteki Zotero i prowadzenia konwersacji z dokumentami.

## Wymagania

- Python 3.8+
- Konto Zotero z API key
- Klucz API OpenAI

## Instalacja

1. Zainstaluj wymagane pakiety:
```bash
pip install pyzotero docling lancedb openai streamlit python-dotenv
```

2. Skonfiguruj plik `.env` z danymi dostępowymi:
```
ZOTERO_USER_ID=your_user_id
ZOTERO_API_KEY=your_api_key
ZOTERO_LIBRARY_TYPE=user
OPENAI_API_KEY=your_openai_api_key
```

## Użytkowanie

### 1. Ekstrakcja dokumentów z Zotero
```bash
python 1-extraction.py
```
Pobiera wszystkie PDF-y z biblioteki Zotero i ekstraktuje z nich tekst.

### 2. Dzielenie na fragmenty
```bash
python 2-chunking.py
```
Dzieli wyekstraktowane dokumenty na mniejsze fragmenty z zachowaniem metadanych Zotero.

### 3. Tworzenie embeddingów i bazy danych
```bash
python 3-embedding.py
```
Tworzy embeddingi dla fragmentów i zapisuje je w bazie danych LanceDB.

### 4. Wyszukiwanie
```bash
python 4-search.py
```
Przykłady wyszukiwania w bazie wiedzy.

### 5. Chatbot
```bash
streamlit run 5-chat.py
```
Uruchamia interfejs webowy do konwersacji z bazą wiedzy.

## Struktura plików

- `utils/zotero_handler.py` - Funkcje do obsługi API Zotero
- `data/zotero_docs.pkl` - Wyekstraktowane dokumenty
- `data/zotero_chunks.pkl` - Fragmenty dokumentów
- `data/lancedb/` - Baza danych z embeddingami

## Metadane Zotero

System zachowuje następujące metadane z Zotero:
- Klucz dokumentu (zotero_key)
- Tytuł (title)
- Autorzy (creators)
- Data publikacji (date)
- Typ elementu (item_type)
- Numery stron (page_numbers)

## Funkcje

- **Automatyczne pobieranie PDF-ów** z biblioteki Zotero
- **Inteligentne dzielenie tekstu** z zachowaniem kontekstu
- **Wyszukiwanie semantyczne** w dokumentach
- **Chatbot z kontekstem** oparty na GPT-4
- **Metadane źródłowe** dla każdego fragmentu

## Architektura

System składa się z pięciu głównych komponentów:

1. **Zotero Handler** (`utils/zotero_handler.py`) - Obsługa API Zotero
2. **Extraction** (`1-extraction.py`) - Pobieranie i ekstrakcja PDF-ów
3. **Chunking** (`2-chunking.py`) - Dzielenie dokumentów na fragmenty
4. **Embedding** (`3-embedding.py`) - Tworzenie embeddingów i bazy danych
5. **Search & Chat** (`4-search.py`, `5-chat.py`) - Wyszukiwanie i interfejs chatbota

## Technologie

- **Zotero API** - Pobieranie dokumentów z biblioteki
- **Docling** - Ekstrakcja tekstu z PDF-ów
- **OpenAI Embeddings** - Tworzenie reprezentacji wektorowych
- **LanceDB** - Baza danych wektorowych
- **Streamlit** - Interfejs webowy chatbota
- **GPT-4** - Model językowy do odpowiedzi