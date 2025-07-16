import lancedb
import pandas as pd
from typing import List, Dict, Any

# --------------------------------------------------------------
# Connect to the database
# --------------------------------------------------------------

uri = "data/lancedb"
db = lancedb.connect(uri)

# --------------------------------------------------------------
# Load the table
# --------------------------------------------------------------

table = db.open_table("docling")

# --------------------------------------------------------------
# Search functions
# --------------------------------------------------------------

def search_zotero_knowledge_base(query: str, limit: int = 5) -> pd.DataFrame:
    """Wyszukuje w bazie wiedzy Zotero i zwraca wyniki z metadanymi."""
    print(f"Wyszukiwanie: '{query}'")
    print("-" * 50)
    
    result = table.search(query=query, query_type="vector").limit(limit)
    df = result.to_pandas()
    
    if df.empty:
        print("Nie znaleziono wyników.")
        return df
    
    # Wyświetl wyniki w czytelnej formie
    for i, row in df.iterrows():
        print(f"\n=== Wynik {i+1} ===")
        print(f"Tytuł: {row['metadata']['title'] or 'Brak tytułu'}")
        print(f"Autorzy: {row['metadata']['creators'] or 'Brak autorów'}")
        print(f"Data: {row['metadata']['date'] or 'Brak daty'}")
        print(f"Typ: {row['metadata']['item_type'] or 'Nieznany'}")
        print(f"Strony: {row['metadata']['page_numbers'] or 'Brak informacji o stronach'}")
        print(f"Klucz Zotero: {row['metadata']['zotero_key'] or 'Brak klucza'}")
        print(f"\nTreść fragmentu:")
        print(f"{row['text'][:300]}{'...' if len(row['text']) > 300 else ''}")
        print("-" * 50)
    
    return df

def search_by_author(author: str, limit: int = 5) -> pd.DataFrame:
    """Wyszukuje dokumenty według autora."""
    print(f"Wyszukiwanie dokumentów autora: '{author}'")
    print("-" * 50)
    
    # Wyszukiwanie w metadanych autorów
    result = table.search(query=author, query_type="vector").limit(limit * 2)
    df = result.to_pandas()
    
    if df.empty:
        print("Nie znaleziono wyników.")
        return df
    
    # Filtruj wyniki zawierające autora w metadanych
    filtered_df = df[df['metadata'].apply(
        lambda x: author.lower() in (x.get('creators') or '').lower()
    )].head(limit)
    
    if filtered_df.empty:
        print("Nie znaleziono dokumentów tego autora.")
        return filtered_df
    
    for i, row in filtered_df.iterrows():
        print(f"\n=== Dokument {i+1} ===")
        print(f"Tytuł: {row['metadata']['title'] or 'Brak tytułu'}")
        print(f"Autorzy: {row['metadata']['creators'] or 'Brak autorów'}")
        print(f"Data: {row['metadata']['date'] or 'Brak daty'}")
        print("-" * 30)
    
    return filtered_df

# --------------------------------------------------------------
# Example searches
# --------------------------------------------------------------

if __name__ == "__main__":
    # Przykładowe wyszukiwania
    print("=== WYSZUKIWANIE W BAZIE WIEDZY ZOTERO ===")
    print(f"Liczba dokumentów w bazie: {table.count_rows()}")
    print()
    
    # Wyszukiwanie ogólne
    search_results = search_zotero_knowledge_base("machine learning", limit=3)
    
    print("\n" + "=" * 60)
    
    # Wyszukiwanie według autora (przykład)
    # author_results = search_by_author("Smith", limit=3)
