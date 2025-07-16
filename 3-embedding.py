from typing import List
import pickle
import os

import lancedb
from docling.chunking import HybridChunker
from dotenv import load_dotenv
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
from openai import OpenAI
from utils.tokenizer import OpenAITokenizerWrapper

load_dotenv()

# Initialize OpenAI client (make sure you have OPENAI_API_KEY in your environment variables)
client = OpenAI()

tokenizer = OpenAITokenizerWrapper()  # Load our custom tokenizer for OpenAI
MAX_TOKENS = 8191  # text-embedding-3-large's maximum context length

# --------------------------------------------------------------
# Load chunks from Zotero documents
# --------------------------------------------------------------

def load_zotero_chunks():
    """Wczytuje fragmenty dokumentów z Zotero."""
    chunks_file = "data/zotero_chunks.pkl"
    
    if not os.path.exists(chunks_file):
        print("Plik z fragmentami nie istnieje. Uruchom najpierw 2-chunking.py")
        return []
    
    with open(chunks_file, 'rb') as f:
        chunks_data = pickle.load(f)
    
    print(f"Wczytano {len(chunks_data)} fragmentów z pliku {chunks_file}")
    return chunks_data

# Get the OpenAI embedding function
func = get_registry().get("openai").create(name="text-embedding-3-large")

# Define a simplified metadata schema for Zotero documents
class ChunkMetadata(LanceModel):
    """
    You must order the fields in alphabetical order.
    This is a requirement of the Pydantic implementation.
    """

    creators: str | None  # Autorzy jako string
    date: str | None
    item_type: str | None
    page_numbers: List[int] | None
    title: str | None
    zotero_key: str | None

# Define the main Schema
class Chunks(LanceModel):
    text: str = func.SourceField()
    vector: Vector(func.ndims()) = func.VectorField()  # type: ignore
    metadata: ChunkMetadata

def create_embeddings():
    """Tworzy embeddingi z chunków i zapisuje do bazy LanceDB."""
    chunks_data = load_zotero_chunks()
    if not chunks_data:
        print("Brak fragmentów do przetworzenia. Uruchom najpierw 2-chunking.py")
        return None

    # Create a LanceDB database
    db = lancedb.connect("data/lancedb")
    
    # Sprawdź czy tabela już istnieje
    try:
        existing_table = db.open_table("docling")
        existing_count = existing_table.count_rows()
        print(f"\nZnaleziono istniejącą bazę danych z {existing_count} embeddingami.")
        print("Czy chcesz:")
        print("1. Użyć istniejącej bazy danych")
        print("2. Utworzyć nową bazę danych (nadpisze istniejącą)")
        choice = input("Wybierz opcję (1/2): ").strip()
        
        if choice == "1":
            print("Używam istniejącej bazy danych.")
            return existing_table
        else:
            print("Tworzę nową bazę danych...")
            table = db.create_table("docling", schema=Chunks, mode="overwrite")
    except:
        print("Tworzę nową bazę danych...")
        table = db.create_table("docling", schema=Chunks, mode="overwrite")
    
    return process_and_add_chunks(chunks_data, table)

def process_and_add_chunks(chunks_data, table):
    """Przetwarza chunki i dodaje je do tabeli."""

    def format_creators(creators_list):
        """Formatuje listę twórców do stringa."""
        if not creators_list:
            return None
        
        formatted = []
        for creator in creators_list:
            if isinstance(creator, dict):
                name_parts = []
                if 'firstName' in creator:
                    name_parts.append(creator['firstName'])
                if 'lastName' in creator:
                    name_parts.append(creator['lastName'])
                if name_parts:
                    formatted.append(' '.join(name_parts))
            else:
                formatted.append(str(creator))
        
        return ', '.join(formatted) if formatted else None

    # Create table with processed chunks from Zotero
    processed_chunks = []
    print(f"Przetwarzanie {len(chunks_data)} fragmentów...")
    
    for chunk_info in chunks_data:
        chunk = chunk_info['chunk']
        # Poprawka: metadane są bezpośrednio w chunk_info, nie w chunk_info['metadata']
        
        processed_chunk = {
            "text": chunk.text,
            "metadata": {
                "zotero_key": chunk_info.get('zotero_key'),
                "title": chunk_info.get('title'),
                "creators": format_creators(chunk_info.get('creators')),
                "date": chunk_info.get('date'),
                "item_type": chunk_info.get('item_type'),
                "page_numbers": [
                    page_no
                    for page_no in sorted(
                        set(
                            prov.page_no
                            for item in chunk.meta.doc_items
                            for prov in item.prov
                        )
                    )
                ] or None,
            },
        }
        processed_chunks.append(processed_chunk)

    print(f"Przygotowano {len(processed_chunks)} fragmentów do dodania do bazy danych")
    print("Dodawanie fragmentów do bazy danych (tworzenie embeddingów)...")
    
    # Add the chunks to the table (automatically embeds the text)
    table.add(processed_chunks)
    
    print(f"Pomyślnie dodano {len(processed_chunks)} fragmentów do bazy danych")
    print(f"Łączna liczba rekordów w bazie: {table.count_rows()}")
    
    return table

# --------------------------------------------------------------
# Main execution
# --------------------------------------------------------------

if __name__ == "__main__":
    table = create_embeddings()
    if table:
        print("\nBaza danych embeddingów jest gotowa do użycia!")
        print(f"Ścieżka do bazy: data/lancedb")
        print(f"Nazwa tabeli: docling")
    else:
        print("Nie udało się utworzyć bazy danych embeddingów.")
