from typing import List, Dict, Any
from docling.chunking import HybridChunker
from dotenv import load_dotenv
from openai import OpenAI
from utils.tokenizer import OpenAITokenizerWrapper
from utils.zotero_handler import extract_documents_from_zotero
import pickle
import os
import hashlib
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import time

load_dotenv()

# Initialize OpenAI client (make sure you have OPENAI_API_KEY in your environment variables)
client = OpenAI()

tokenizer = OpenAITokenizerWrapper()  # Load our custom tokenizer for OpenAI
MAX_TOKENS = 8191  # text-embedding-3-large's maximum context length

def get_chunks_cache_filename(zotero_key: str) -> str:
    """Generuje nazwę pliku cache dla chunków dokumentu."""
    hash_key = hashlib.md5(zotero_key.encode()).hexdigest()
    return f"data/chunks_cache/{hash_key}_chunks.pkl"

def load_cached_chunks(cache_path: str) -> List[Dict[str, Any]]:
    """Wczytuje chunki z cache."""
    with open(cache_path, 'rb') as f:
        return pickle.load(f)

def save_chunks_to_cache(chunks: List[Dict[str, Any]], cache_path: str):
    """Zapisuje chunki do cache."""
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'wb') as f:
        pickle.dump(chunks, f)

def process_single_document_chunks(doc_data: Dict[str, Any]) -> Dict[str, Any]:
    """Przetwarza chunking dla pojedynczego dokumentu.
    
    Args:
        doc_data: Słownik zawierający dane dokumentu i konfigurację
        
    Returns:
        Słownik z wynikami chunkingu lub informacją o błędzie
    """
    try:
        doc_info = doc_data['doc_info']
        max_tokens = doc_data['max_tokens']
        
        zotero_key = doc_info['zotero_key']
        chunks_cache_path = get_chunks_cache_filename(zotero_key)
        
        # Sprawdź czy chunki już zostały utworzone
        if os.path.exists(chunks_cache_path):
            try:
                cached_chunks = load_cached_chunks(chunks_cache_path)
                return {
                    'success': True,
                    'cached': True,
                    'chunks': cached_chunks,
                    'title': doc_info['title'],
                    'chunk_count': len(cached_chunks)
                }
            except Exception as e:
                # Usuń uszkodzony plik cache i kontynuuj przetwarzanie
                try:
                    os.unlink(chunks_cache_path)
                except:
                    pass
        
        # Utwórz tokenizer i chunker dla tego procesu
        tokenizer = OpenAITokenizerWrapper()
        chunker = HybridChunker(
            tokenizer=tokenizer,
            max_tokens=max_tokens,
            merge_peers=True,
        )
        
        try:
            # Wykonaj chunking
            chunk_iter = chunker.chunk(dl_doc=doc_info['document'])
            doc_chunks = list(chunk_iter)
            
            # Dodaj metadane Zotero do każdego chunka
            chunks_with_metadata = []
            for chunk in doc_chunks:
                chunk_with_metadata = {
                    'chunk': chunk,
                    'zotero_key': doc_info['zotero_key'],
                    'title': doc_info['title'],
                    'creators': doc_info['creators'],
                    'date': doc_info['date'],
                    'item_type': doc_info['item_type'],
                    'pdf_size': doc_info['pdf_size']
                }
                chunks_with_metadata.append(chunk_with_metadata)
            
            # Zapisz chunki do cache
            save_chunks_to_cache(chunks_with_metadata, chunks_cache_path)
            
            return {
                'success': True,
                'cached': False,
                'chunks': chunks_with_metadata,
                'title': doc_info['title'],
                'chunk_count': len(doc_chunks)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Błąd podczas chunkingu: {str(e)}",
                'title': doc_info['title']
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Błąd ogólny: {str(e)}",
            'title': 'Nieznany dokument'
        }

def chunk_zotero_documents(docs: List[Dict[str, Any]], max_workers: int = None) -> List[Dict[str, Any]]:
    """Dzieli dokumenty z Zotero na chunki z zachowaniem metadanych używając multiprocessing.
    
    Args:
        docs: Lista dokumentów do przetworzenia
        max_workers: Maksymalna liczba procesów roboczych. Jeśli None, użyje liczby CPU.
    
    Zapisuje chunki każdego dokumentu osobno i pomija już przetworzone.
    """
    print(f"Rozpoczynam chunking {len(docs)} dokumentów...")
    
    # Utwórz katalog cache dla chunków jeśli nie istnieje
    os.makedirs("data/chunks_cache", exist_ok=True)
    
    # Określ liczbę procesów roboczych
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), len(docs))
    
    print(f"Używanie {max_workers} procesów roboczych dla chunkingu {len(docs)} dokumentów")
    
    all_chunks = []
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    # Przygotuj dane dla procesów roboczych
    docs_data = [{
        'doc_info': doc_info,
        'max_tokens': MAX_TOKENS
    } for doc_info in docs]
    
    # Użyj ProcessPoolExecutor dla równoległego przetwarzania
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Uruchom zadania
        future_to_doc = {executor.submit(process_single_document_chunks, doc_data): doc_data 
                        for doc_data in docs_data}
        
        # Przetwarzaj wyniki w miarę ich ukończenia
        with tqdm(total=len(docs), desc="Chunking dokumentów") as pbar:
            for future in as_completed(future_to_doc):
                try:
                    result = future.result()
                    
                    if result['success']:
                        all_chunks.extend(result['chunks'])
                        
                        if result.get('cached', False):
                            skipped_count += 1
                            tqdm.write(f"  ⚡ Wczytano chunki z cache: {result['title']} ({result['chunk_count']} chunków)")
                        else:
                            processed_count += 1
                            tqdm.write(f"  ✓ Przetworzono chunki: {result['title']} ({result['chunk_count']} chunków)")
                    else:
                        error_count += 1
                        tqdm.write(f"  ❌ Błąd: {result['title']} - {result['error']}")
                        
                except Exception as e:
                    error_count += 1
                    tqdm.write(f"  ❌ Nieoczekiwany błąd w procesie: {str(e)}")
                
                pbar.update(1)
    
    print(f"\nPodsumowanie chunkingu (multiprocessing):")
    print(f"  Nowo przetworzonych dokumentów: {processed_count}")
    print(f"  Wczytanych z cache: {skipped_count}")
    print(f"  Błędów: {error_count}")
    print(f"  Łącznie chunków: {len(all_chunks)}")
    print(f"  Użyto procesów: {max_workers}")
    return all_chunks

def save_chunks(chunks: List[Dict[str, Any]], filename: str = "data/zotero_chunks.pkl"):
    """Zapisuje chunki do pliku."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'wb') as f:
        pickle.dump(chunks, f)
    print(f"Zapisano {len(chunks)} chunków do {filename}")

def load_chunks(filename: str = "data/zotero_chunks.pkl") -> List[Dict[str, Any]]:
    """Wczytuje chunki z pliku."""
    with open(filename, 'rb') as f:
        chunks = pickle.load(f)
    print(f"Wczytano {len(chunks)} chunków z {filename}")
    return chunks

# --------------------------------------------------------------
# Pobierz dokumenty z Zotero i wykonaj chunking
# --------------------------------------------------------------

if __name__ == "__main__":
    # Sprawdź czy istnieją już wyekstraktowane dokumenty
    docs_file = "data/zotero_docs.pkl"
    chunks_file = "data/zotero_chunks.pkl"
    
    if os.path.exists(docs_file):
        print("Wczytywanie wcześniej wyekstraktowanych dokumentów...")
        with open(docs_file, 'rb') as f:
            docs = pickle.load(f)
    else:
        print("Ekstraktowanie dokumentów z Zotero...")
        docs = extract_documents_from_zotero()
        
        # Zapisz dokumenty dla przyszłego użycia
        os.makedirs("data", exist_ok=True)
        with open(docs_file, 'wb') as f:
            pickle.dump(docs, f)
        print(f"Zapisano {len(docs)} dokumentów do {docs_file}")
    
    # Sprawdź czy główny plik chunków już istnieje
    if os.path.exists(chunks_file):
        print(f"\nGłówny plik chunków {chunks_file} już istnieje.")
        print("Czy chcesz:")
        print("1. Wczytać istniejące chunki")
        print("2. Uruchomić ponownie chunking (wykorzysta cache dla już przetworzonych)")
        choice = input("Wybierz opcję (1/2): ").strip()
        
        if choice == "1":
            chunks = load_chunks(chunks_file)
        else:
            # Konfiguracja multiprocessing
            max_cpu = multiprocessing.cpu_count()
            print(f"\nKonfiguracja multiprocessing dla chunkingu:")
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
            
            print(f"\nRozpoczynanie chunkingu z {max_workers} procesami...")
            start_time = time.time()
            chunks = chunk_zotero_documents(docs, max_workers=max_workers)
            end_time = time.time()
            
            processing_time = end_time - start_time
            print(f"\nCzas chunkingu: {processing_time:.2f} sekund")
            if len(docs) > 0:
                print(f"Średni czas na dokument: {processing_time/len(docs):.2f} sekund")
            
            # Zapisz chunki
            save_chunks(chunks)
    else:
        # Konfiguracja multiprocessing dla nowego chunkingu
        max_cpu = multiprocessing.cpu_count()
        print(f"\nKonfiguracja multiprocessing dla chunkingu:")
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
        
        print(f"\nRozpoczynanie chunkingu z {max_workers} procesami...")
        start_time = time.time()
        chunks = chunk_zotero_documents(docs, max_workers=max_workers)
        end_time = time.time()
        
        processing_time = end_time - start_time
        print(f"\nCzas chunkingu: {processing_time:.2f} sekund")
        if len(docs) > 0:
            print(f"Średni czas na dokument: {processing_time/len(docs):.2f} sekund")
        
        # Zapisz chunki
        save_chunks(chunks)
    
    # Wyświetl statystyki
    print(f"\nStatystyki:")
    print(f"Dokumenty: {len(docs)}")
    print(f"Chunki: {len(chunks)}")
    if len(docs) > 0:
        print(f"Średnio chunków na dokument: {len(chunks)/len(docs):.1f}")
    
    # Wyświetl informacje o cache chunków
    chunks_cache_dir = "data/chunks_cache"
    if os.path.exists(chunks_cache_dir):
        cache_files = [f for f in os.listdir(chunks_cache_dir) if f.endswith('.pkl')]
        print(f"Liczba plików w cache chunków: {len(cache_files)}")
    
    # Przykład chunka
    if chunks:
        first_chunk = chunks[0]
        print(f"\nPierwszy chunk z dokumentu '{first_chunk['title']}':")
        print(f"Tekst (pierwsze 200 znaków): {first_chunk['chunk'].text[:200]}...")
        print(f"Typ dokumentu: {first_chunk['item_type']}")
        print(f"Data: {first_chunk['date']}")
