import os
from dotenv import load_dotenv
import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

# .env 
load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

CV_DIRECTORY = "sample_cvs"
PERSIST_DIRECTORY = "chroma_db_store" # Vector DB එක save කරන ෆෝල්ඩරයේ නම

def load_documents_from_directory(directory):
    """text and metadata load"""
    documents = []
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Metadata 
                metadata = {"candidate_id": filename.split('.')[0], "source": filepath}
                documents.append({"content": content, "metadata": metadata})
    return documents

print("Loading CV documents...")
cv_data = load_documents_from_directory(CV_DIRECTORY)
if not cv_data:
    print("No CV documents found. Please check the 'sample_cvs' directory.")
else:
    # Embedding model (Gemini)
    gemini_embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # ChromaDB vector store 
    print(f"Creating and persisting Vector Database at: {PERSIST_DIRECTORY}")
    
    # Texts and  metadata
    texts = [doc['content'] for doc in cv_data]
    metadatas = [doc['metadata'] for doc in cv_data]

    # Vector store create, embeddings data store
    vector_store = Chroma.from_texts(
        texts=texts,
        embedding=gemini_embeddings,
        metadatas=metadatas,
        persist_directory=PERSIST_DIRECTORY
    )
    
    print("Vector Database setup complete!")
    print(f"Total documents indexed: {vector_store._collection.count()}")