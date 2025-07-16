# System Cache'owania - Zotero Knowledge Base

## Przegląd

Aplikacja została zmodyfikowana, aby zapisywać każdy przetworzony plik osobno i nie przetwarzać plików dwukrotnie. Dzięki temu można bezpiecznie przerywać proces bez utraty już przetworzonych danych.

## Struktura Cache'u

### 1. Cache Dokumentów (`data/cache/`)
- **Lokalizacja**: `data/cache/`
- **Format plików**: `{hash}.pkl`
- **Zawartość**: Pojedyncze przetworzone dokumenty z Zotero
- **Klucz**: Hash MD5 z kombinacji `zotero_key_attachment_key`

### 2. Cache Chunków (`data/chunks_cache/`)
- **Lokalizacja**: `data/chunks_cache/`
- **Format plików**: `{hash}_chunks.pkl`
- **Zawartość**: Chunki dla pojedynczego dokumentu
- **Klucz**: Hash MD5 z `zotero_key`

### 3. Główne Pliki
- **`data/zotero_docs.pkl`**: Wszystkie przetworzone dokumenty (dla kompatybilności)
- **`data/zotero_chunks.pkl`**: Wszystkie chunki (dla kompatybilności)
- **`data/lancedb/`**: Baza danych embeddingów

## Jak Działa System

### 1-extraction.py (z Multiprocessing)
1. Sprawdza czy główny plik `zotero_docs.pkl` już istnieje
2. Konfiguruje liczbę procesów roboczych (domyślnie liczba CPU)
3. Używa ProcessPoolExecutor do równoległego przetwarzania dokumentów
4. Każdy proces sprawdza cache w `data/cache/` przed przetwarzaniem
5. Jeśli dokument jest w cache - wczytuje go
6. Jeśli nie - pobiera PDF, przetwarza i zapisuje do cache
7. Na końcu zapisuje wszystkie dokumenty do głównego pliku
8. Wyświetla statystyki wydajności (czas, średni czas na dokument)

### 2-chunking.py (z Multiprocessing)
1. Sprawdza czy główny plik `zotero_chunks.pkl` już istnieje
2. Konfiguruje liczbę procesów roboczych (domyślnie liczba CPU)
3. Używa ProcessPoolExecutor do równoległego chunkingu dokumentów
4. Każdy proces sprawdza cache chunków w `data/chunks_cache/`
5. Jeśli chunki są w cache - wczytuje je
6. Jeśli nie - tworzy chunki i zapisuje do cache
7. Na końcu zapisuje wszystkie chunki do głównego pliku
8. Wyświetla statystyki wydajności (czas, średni czas na dokument)

### 3-embedding.py
1. Sprawdza czy baza danych LanceDB już istnieje
2. Oferuje opcję użycia istniejącej bazy lub utworzenia nowej
3. Jeśli tworzy nową - przetwarza wszystkie chunki

## Korzyści

✅ **Odporność na przerwania**: Można bezpiecznie przerwać proces w dowolnym momencie

✅ **Szybsze ponowne uruchomienie**: Już przetworzone pliki są pomijane

✅ **Oszczędność zasobów**: Nie marnuje się czas na ponowne przetwarzanie

✅ **Elastyczność**: Można wybrać czy użyć cache czy przetwarzać od nowa

✅ **Multiprocessing**: Równoległe przetwarzanie wykorzystuje wszystkie rdzenie CPU

✅ **Skalowalność**: Konfigurowalny poziom równoległości (1 do liczby CPU)

✅ **Monitorowanie wydajności**: Pomiar czasu i statystyki przetwarzania

✅ **Inteligentne zarządzanie zasobami**: Automatyczne dostosowanie liczby procesów

## Zarządzanie Cache'em

### Sprawdzenie Stanu Cache'u
```bash
# Liczba dokumentów w cache
ls data/cache/*.pkl | wc -l

# Liczba chunków w cache
ls data/chunks_cache/*.pkl | wc -l

# Rozmiar cache'u
du -sh data/cache/
du -sh data/chunks_cache/
```

### Czyszczenie Cache'u
```bash
# Usuń cache dokumentów
rm -rf data/cache/

# Usuń cache chunków
rm -rf data/chunks_cache/

# Usuń wszystkie cache i główne pliki
rm -rf data/
```

### Częściowe Czyszczenie
```bash
# Usuń tylko uszkodzone pliki cache (jeśli są problemy)
find data/cache/ -name "*.pkl" -size 0 -delete
find data/chunks_cache/ -name "*.pkl" -size 0 -delete
```

## Opcje Uruchomienia

### 1-extraction.py
- **Opcja 1**: Wczytaj istniejące dokumenty z głównego pliku
- **Opcja 2**: Uruchom ekstrakcję (wykorzysta cache dla już przetworzonych)
  - Konfiguracja liczby procesów roboczych (1 do liczby CPU)
  - Pomiar czasu przetwarzania i statystyki wydajności

### 2-chunking.py
- **Opcja 1**: Wczytaj istniejące chunki z głównego pliku
- **Opcja 2**: Uruchom chunking (wykorzysta cache dla już przetworzonych)
  - Konfiguracja liczby procesów roboczych (1 do liczby CPU)
  - Pomiar czasu chunkingu i statystyki wydajności

### 3-embedding.py
- **Opcja 1**: Użyj istniejącej bazy danych
- **Opcja 2**: Utwórz nową bazę danych (nadpisze istniejącą)

## Rozwiązywanie Problemów

### Problem: Uszkodzone pliki cache
**Rozwiązanie**: Usuń uszkodzone pliki - system automatycznie je odtworzy
```bash
rm data/cache/{problematyczny_hash}.pkl
```

### Problem: Nieaktualne cache po zmianie w Zotero
**Rozwiązanie**: Usuń cache dla konkretnego dokumentu lub cały cache
```bash
# Usuń cały cache aby wymusić ponowne przetwarzanie
rm -rf data/cache/ data/chunks_cache/
```

### Problem: Brak miejsca na dysku
**Rozwiązanie**: Cache może zajmować dużo miejsca - można go bezpiecznie usunąć
```bash
du -sh data/  # sprawdź rozmiar
rm -rf data/cache/ data/chunks_cache/  # usuń cache
```

## Wydajność Multiprocessing

### Zalety
- **Przyspieszone przetwarzanie**: Wykorzystanie wszystkich rdzeni CPU
- **Równoległe operacje**: Pobieranie i konwersja PDF-ów jednocześnie
- **Skalowalność**: Automatyczne dostosowanie do sprzętu
- **Efektywność**: Lepsze wykorzystanie zasobów systemowych

### Konfiguracja
- **Domyślna**: Liczba procesów = liczba rdzeni CPU
- **Minimalna**: 1 proces (tryb sekwencyjny)
- **Maksymalna**: Liczba rdzeni CPU
- **Zalecana**: Pełna liczba CPU dla najlepszej wydajności

### Uwagi
- Każdy proces używa własnej pamięci
- Większa liczba procesów = większe zużycie RAM
- Dla małej liczby dokumentów (< 4) multiprocessing może być wolniejszy
- Cache znacznie przyspiesza ponowne uruchomienia

## Kompatybilność

System jest w pełni kompatybilny z poprzednią wersją:
- Główne pliki (`zotero_docs.pkl`, `zotero_chunks.pkl`) są nadal tworzone
- Skrypty 4-search.py i 5-chat.py działają bez zmian
- Można migrować stopniowo - stare pliki będą działać
- Multiprocessing jest opcjonalny - można użyć 1 procesu

## Monitorowanie Postępu

Każdy skrypt pokazuje:
- Liczbę nowo przetworzonych elementów
- Liczbę wczytanych z cache
- Liczbę błędów (jeśli wystąpiły)
- Łączną liczbę elementów
- Liczbę użytych procesów
- Czas przetwarzania i średni czas na element
- Lokalizację plików cache

Przykład (extraction):
```
Podsumowanie (multiprocessing):
  Nowo przetworzonych: 5
  Wczytanych z cache: 15
  Błędów: 0
  Łącznie dokumentów: 20
  Użyto procesów: 8

Czas przetwarzania: 45.32 sekund
Średni czas na dokument: 2.27 sekund
Liczba plików w cache: 20
```

Przykład (chunking):
```
Podsumowanie chunkingu (multiprocessing):
  Nowo przetworzonych dokumentów: 3
  Wczytanych z cache: 17
  Błędów: 0
  Łącznie chunków: 156
  Użyto procesów: 8

Czas chunkingu: 12.45 sekund
Średni czas na dokument: 0.62 sekund
```