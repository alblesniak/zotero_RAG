import pickle
import os
import multiprocessing
import time
from utils.zotero_handler import extract_documents_from_zotero

# --------------------------------------------------------------
# Ekstraktuj dokumenty z biblioteki Zotero
# --------------------------------------------------------------

if __name__ == "__main__":
    # Sprawdź czy główny plik już istnieje
    main_docs_file = "data/zotero_docs.pkl"
    
    if os.path.exists(main_docs_file):
        print(f"Główny plik {main_docs_file} już istnieje.")
        print("Czy chcesz:")
        print("1. Wczytać istniejące dokumenty")
        print("2. Uruchomić ponownie ekstrakcję (wykorzysta cache dla już przetworzonych)")
        choice = input("Wybierz opcję (1/2): ").strip()
        
        if choice == "1":
            with open(main_docs_file, 'rb') as f:
                docs = pickle.load(f)
            print(f"Wczytano {len(docs)} dokumentów z {main_docs_file}")
        else:
            # Konfiguracja multiprocessing
            max_cpu = multiprocessing.cpu_count()
            print(f"\nKonfiguracja multiprocessing:")
            print(f"Dostępne rdzenie CPU: {max_cpu}")
            print(f"Zalecana liczba procesów: {max_cpu}")
            
            while True:
                try:
                    workers_input = input(f"Liczba procesów roboczych (1-{max_cpu}, Enter dla {max_cpu}): ").strip()
                    if workers_input == "":
                        max_workers = max_cpu
                        break
                    max_workers = int(workers_input)
                    if 1 <= max_workers <= max_cpu:
                        break
                    else:
                        print(f"Proszę podać liczbę między 1 a {max_cpu}")
                except ValueError:
                    print("Proszę podać prawidłową liczbę")
            
            print(f"\nRozpoczynanie ekstrakcji z {max_workers} procesami...")
            start_time = time.time()
            docs = extract_documents_from_zotero(max_workers=max_workers)
            end_time = time.time()
            
            processing_time = end_time - start_time
            print(f"\nCzas przetwarzania: {processing_time:.2f} sekund")
            if len(docs) > 0:
                print(f"Średni czas na dokument: {processing_time/len(docs):.2f} sekund")
    else:
        # Konfiguracja multiprocessing dla nowej ekstrakcji
        max_cpu = multiprocessing.cpu_count()
        print(f"Konfiguracja multiprocessing:")
        print(f"Dostępne rdzenie CPU: {max_cpu}")
        print(f"Zalecana liczba procesów: {max_cpu}")
        
        while True:
            try:
                workers_input = input(f"Liczba procesów roboczych (1-{max_cpu}, Enter dla {max_cpu}): ").strip()
                if workers_input == "":
                    max_workers = max_cpu
                    break
                max_workers = int(workers_input)
                if 1 <= max_workers <= max_cpu:
                    break
                else:
                    print(f"Proszę podać liczbę między 1 a {max_cpu}")
            except ValueError:
                print("Proszę podać prawidłową liczbę")
        
        print(f"\nRozpoczynanie ekstrakcji z {max_workers} procesami...")
        start_time = time.time()
        docs = extract_documents_from_zotero(max_workers=max_workers)
        end_time = time.time()
        
        processing_time = end_time - start_time
        print(f"\nCzas przetwarzania: {processing_time:.2f} sekund")
        if len(docs) > 0:
            print(f"Średni czas na dokument: {processing_time/len(docs):.2f} sekund")
    
    # Przykład użycia - wyświetl informacje o pierwszym dokumencie
    if docs:
        first_doc = docs[0]
        print(f"\nPierwszy dokument: {first_doc['title']}")
        print(f"Typ: {first_doc['item_type']}")
        print(f"Data: {first_doc['date']}")
        print(f"Rozmiar PDF: {first_doc['pdf_size']} bajtów")
        
        # Eksportuj do markdown
        # Sprawdź, czy obiekt dokumentu istnieje i ma metodę export_to_markdown
        if hasattr(first_doc.get('document'), 'export_to_markdown'):
            markdown_output = first_doc['document'].export_to_markdown()
            print(f"\nPodgląd treści (pierwsze 500 znaków):\n{markdown_output[:500]}...")

    # Zapisz wyekstraktowane dokumenty do głównego pliku pickle
    if docs:
        output_dir = 'data'
        output_path = os.path.join(output_dir, 'zotero_docs.pkl')
        os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            pickle.dump(docs, f)
        
        print(f"\nPomyślnie zapisano {len(docs)} dokumentów do pliku {output_path}")
        print(f"Indywidualne dokumenty są również zapisane w katalogu data/cache/")
        
        # Wyświetl informacje o cache
        cache_dir = "data/cache"
        if os.path.exists(cache_dir):
            cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl')]
            print(f"Liczba plików w cache: {len(cache_files)}")
