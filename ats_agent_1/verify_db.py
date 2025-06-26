import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

# Load environment variables (ensure your .env file has the API key)
load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    raise ValueError("GOOGLE_API_KEY not found in .env file.")

PERSIST_DIRECTORY = "chroma_db_store"

print("--- Vector Database Verification Script ---")

if not os.path.exists(PERSIST_DIRECTORY):
    print(f"ERROR: The database directory '{PERSIST_DIRECTORY}' does not exist.")
    print("Please run 'python setup_vector_db.py' first.")
else:
    try:
        # Initialize the embedding model and load the vector store from disk
        print("Loading existing vector store from disk...")
        gemini_embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vector_store = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=gemini_embeddings
        )
        print("Vector store loaded successfully.")

        # 1. Check the total number of documents in the database
        doc_count = vector_store._collection.count()
        print(f"\n[CHECK 1] Total documents in the database: {doc_count}")
        if doc_count < 13:
            print(f"WARNING: Expected 13 documents (3 old + 10 new), but found only {doc_count}. The setup script may not have run correctly after adding new CVs.")
        
        # 2. Retrieve and display metadata of all stored documents
        print("\n[CHECK 2] Metadata of all stored documents:")
        all_docs = vector_store.get()
        if all_docs and all_docs['ids']:
             for i, metadata in enumerate(all_docs['metadatas']):
                 print(f"  - Doc {i+1}: {metadata}")
        else:
            print("  - No documents found.")

        # 3. Perform a direct search test, bypassing the agent
        print("\n[CHECK 3] Performing a direct search for 'Terraform'...")
        search_query = "Terraform and AWS"
        results = vector_store.similarity_search_with_score(search_query, k=3)

        if results:
            print("SUCCESS: Direct search found the following results:")
            for doc, score in results:
                print(f"  - Found: {doc.metadata.get('candidate_id')}, Score: {score}")
        else:
            print("FAILURE: Direct search did not find any results for the query.")

    except Exception as e:
        print(f"\nAn error occurred while trying to verify the database: {e}")
        print("This could be due to a corrupted database directory or an issue with the embedding model.")