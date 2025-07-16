import os
from typing import List, Dict, Any
from docling.document_converter import DocumentConverter
from pyzotero import zotero
from dotenv import load_dotenv
import requests
import tempfile
from tqdm import tqdm
import pickle
import hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

load_dotenv()

def get_zotero_connection():
    """Tworzy połączenie z Zotero API."""
    ZOTERO_USER_ID = os.getenv('ZOTERO_USER_ID')
    ZOTERO_API_KEY = os.getenv('ZOTERO_API_KEY')
    ZOTERO_LIBRARY_TYPE = os.getenv('ZOTERO_LIBRARY_TYPE')
    
    return zotero.Zotero(ZOTERO_USER_ID, ZOTERO_LIBRARY_TYPE, ZOTERO_API_KEY)

def get_zotero_items_with_pdfs() -> List[Dict[str, Any]]:
    """Pobiera wszystkie elementy z biblioteki Zotero, które mają załączniki PDF."""
    print("Pobieranie elementów z biblioteki Zotero...")
    
    zot = get_zotero_connection()
    # Pobierz wszystkie elementy, w tym załączniki
    all_items = zot.everything(zot.items())
    
    # Słownik do mapowania kluczy rodziców na elementy
    items_map = {item['key']: item for item in all_items if item['data'].get('itemType') != 'attachment'}
    
    # Filtruj załączniki PDF i połącz je z ich rodzicami
    attachments_with_parents = []
    for item in all_items:
        if item['data'].get('itemType') == 'attachment' and item['data'].get('contentType') == 'application/pdf':
            parent_key = item['data'].get('parentItem')
            if parent_key in items_map:
                parent_item = items_map[parent_key]
                # Kopiujemy dane rodzica i dodajemy informacje o załączniku
                combined_item = parent_item.copy()
                combined_item['attachment'] = item['data']
                combined_item['attachment_key'] = item['key']
                attachments_with_parents.append(combined_item)

    print(f"Znaleziono {len(attachments_with_parents)} elementów z załącznikami PDF")
    return attachments_with_parents

def download_pdf_from_zotero(zot: zotero.Zotero, attachment_key: str) -> str:
    """Pobiera PDF z Zotero API i zapisuje do pliku tymczasowego."""
    # Pobierz zawartość pliku PDF
    pdf_content = zot.file(attachment_key)
    
    # Utwórz plik tymczasowy
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.write(pdf_content)
    temp_file.close()
    
    return temp_file.name

def validate_pdf(pdf_path: str) -> int:
    """Sprawdza poprawność pliku PDF i zwraca jego rozmiar.
    
    Args:
        pdf_path: Ścieżka do pliku PDF
        
    Returns:
        Rozmiar pliku w bajtach
        
    Raises:
        ValueError: Gdy plik jest niepoprawny lub uszkodzony
    """
    # Sprawdź rozmiar pliku
    file_size = os.path.getsize(pdf_path)
    if file_size == 0:
        raise ValueError("Pusty plik PDF")
    
    with open(pdf_path, 'rb') as f:
        # Sprawdź nagłówek PDF
        pdf_header = f.read(5)
        if pdf_header != b'%PDF-':
            f.seek(0)
            file_content_preview = f.read(100)
            raise ValueError(f"Nieprawidłowy format pliku PDF. Początek pliku: {file_content_preview!r}")
        
        # Sprawdź czy plik nie jest uszkodzony
        try:
            if file_size > 1024:
                f.seek(-1024, 2)  # Przejdź do końca pliku
            else:
                f.seek(0)  # Dla małych plików czytaj od początku
            trailer = f.read().lower()
            if b'%%eof' not in trailer:
                raise ValueError("Brak znacznika EOF w pliku PDF")
        except IOError as io_err:
            raise ValueError(f"Nie można odczytać końca pliku PDF: {str(io_err)}")
    
    return file_size

def get_cache_filename(zotero_key: str, attachment_key: str) -> str:
    """Generuje nazwę pliku cache dla dokumentu na podstawie kluczy Zotero."""
    # Użyj hash dla bezpiecznej nazwy pliku
    combined_key = f"{zotero_key}_{attachment_key}"
    hash_key = hashlib.md5(combined_key.encode()).hexdigest()
    return f"data/cache/{hash_key}.pkl"

def load_cached_document(cache_path: str) -> Dict[str, Any]:
    """Wczytuje dokument z cache."""
    with open(cache_path, 'rb') as f:
        return pickle.load(f)

def save_document_to_cache(doc_info: Dict[str, Any], cache_path: str):
    """Zapisuje dokument do cache."""
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'wb') as f:
        pickle.dump(doc_info, f)

def process_single_document(item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Przetwarza pojedynczy dokument PDF z Zotero.
    
    Args:
        item_data: Słownik zawierający dane elementu Zotero
        
    Returns:
        Słownik z przetworzonymi danymi dokumentu lub informacją o błędzie
    """
    try:
        # Rozpakuj dane
        item = item_data['item']
        attachment_key = item['attachment_key']
        cache_path = get_cache_filename(item['key'], attachment_key)
        
        # Sprawdź czy dokument już został przetworzony
        if os.path.exists(cache_path):
            try:
                cached_doc = load_cached_document(cache_path)
                return {
                    'success': True,
                    'cached': True,
                    'doc_info': cached_doc,
                    'title': cached_doc['title']
                }
            except Exception as e:
                # Usuń uszkodzony plik cache i kontynuuj przetwarzanie
                try:
                    os.unlink(cache_path)
                except:
                    pass
        
        # Utwórz nowe połączenie Zotero dla tego procesu
        zot = get_zotero_connection()
        converter = DocumentConverter()
        pdf_path = None
        
        try:
            # Pobierz PDF używając klucza załącznika
            pdf_path = download_pdf_from_zotero(zot, attachment_key)
            
            # Sprawdź czy plik PDF jest poprawny
            file_size = validate_pdf(pdf_path)
            result = converter.convert(pdf_path)
            
            if not result.document:
                raise ValueError("Konwersja nie zwróciła dokumentu")
            
            # Dodaj metadane z Zotero
            doc_info = {
                'document': result.document,
                'zotero_key': item['key'],
                'title': item['data'].get('title', 'Bez tytułu'),
                'creators': item['data'].get('creators', []),
                'date': item['data'].get('date', ''),
                'item_type': item['data'].get('itemType', ''),
                'pdf_size': file_size
            }
            
            # Zapisz do cache
            save_document_to_cache(doc_info, cache_path)
            
            return {
                'success': True,
                'cached': False,
                'doc_info': doc_info,
                'title': doc_info['title'],
                'file_size': file_size
            }
            
        except ValueError as ve:
            return {
                'success': False,
                'error': f"Błąd walidacji PDF: {ve}",
                'title': item['data'].get('title', 'Bez tytułu')
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Nieoczekiwany błąd: {str(e)}",
                'title': item['data'].get('title', 'Bez tytułu')
            }
        finally:
            # Zawsze próbuj usunąć plik tymczasowy
            if pdf_path:
                try:
                    os.unlink(pdf_path)
                except Exception:
                    pass
                    
    except Exception as e:
        return {
            'success': False,
            'error': f"Błąd ogólny: {str(e)}",
            'title': 'Nieznany dokument'
        }

def extract_documents_from_zotero(max_workers: int = None) -> List[Dict[str, Any]]:
    """Ekstraktuje dokumenty z wszystkich PDFów w bibliotece Zotero używając multiprocessing.
    
    Args:
        max_workers: Maksymalna liczba procesów roboczych. Jeśli None, użyje liczby CPU.
    
    Zapisuje każdy przetworzony dokument osobno i pomija już przetworzone.
    """
    items_with_pdfs = get_zotero_items_with_pdfs()
    extracted_docs = []
    
    # Utwórz katalog cache jeśli nie istnieje
    os.makedirs("data/cache", exist_ok=True)
    
    # Określ liczbę procesów roboczych
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), len(items_with_pdfs))
    
    print(f"Używanie {max_workers} procesów roboczych dla przetwarzania {len(items_with_pdfs)} dokumentów")
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    # Przygotuj dane dla procesów roboczych
    items_data = [{'item': item} for item in items_with_pdfs]
    
    # Użyj ProcessPoolExecutor dla równoległego przetwarzania
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Uruchom zadania
        future_to_item = {executor.submit(process_single_document, item_data): item_data 
                         for item_data in items_data}
        
        # Przetwarzaj wyniki w miarę ich ukończenia
        with tqdm(total=len(items_with_pdfs), desc="Przetwarzanie dokumentów Zotero") as pbar:
            for future in as_completed(future_to_item):
                try:
                    result = future.result()
                    
                    if result['success']:
                        extracted_docs.append(result['doc_info'])
                        
                        if result.get('cached', False):
                            skipped_count += 1
                            tqdm.write(f"  ⚡ Wczytano z cache: {result['title']}")
                        else:
                            processed_count += 1
                            file_size = result.get('file_size', 0)
                            tqdm.write(f"  ✓ Przetworzono: {result['title']} ({file_size} bajtów)")
                    else:
                        error_count += 1
                        tqdm.write(f"  ❌ Błąd: {result['title']} - {result['error']}")
                        
                except Exception as e:
                    error_count += 1
                    tqdm.write(f"  ❌ Nieoczekiwany błąd w procesie: {str(e)}")
                
                pbar.update(1)
    
    print(f"\nPodsumowanie (multiprocessing):")
    print(f"  Nowo przetworzonych: {processed_count}")
    print(f"  Wczytanych z cache: {skipped_count}")
    print(f"  Błędów: {error_count}")
    print(f"  Łącznie dokumentów: {len(extracted_docs)}")
    print(f"  Użyto procesów: {max_workers}")
    return extracted_docs