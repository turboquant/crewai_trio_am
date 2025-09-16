"""
RAG Search Tool - ChromaDB-based semantic search with embeddings
Provides knowledge retrieval with citations from legal documents and policies
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import re
from crewai.tools import tool

try:
    from chromadb import PersistentClient
    from sentence_transformers import SentenceTransformer
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("Warning: ChromaDB or sentence-transformers not available. RAG search will be limited.")

# Get project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = PROJECT_ROOT / ".chroma"
KNOWLEDGE_DIRS = ["knowledge", "policies", "catalogs"]

# Initialize embedding model (will be loaded on first use)
_embedding_model = None

def _get_embedding_model():
    """Initialize embedding model on first use."""
    global _embedding_model
    if _embedding_model is None and CHROMADB_AVAILABLE:
        try:
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"Warning: Could not load embedding model: {e}")
            _embedding_model = None
    return _embedding_model

def _get_chroma_client():
    """Get ChromaDB client with persistent storage."""
    if not CHROMADB_AVAILABLE:
        return None
    
    try:
        # Ensure directory exists
        CHROMA_DIR.mkdir(exist_ok=True)
        return PersistentClient(path=str(CHROMA_DIR))
    except Exception as e:
        print(f"Warning: Could not initialize ChromaDB client: {e}")
        return None

@tool("rag_search")
def rag_search(query: str, k: int = 5, collection_name: str = "knowledge_base") -> str:
    """
    Perform semantic search across knowledge base documents.
    
    Args:
        query: Search query (e.g., "asset segregation requirements")
        k: Number of results to return (default 5)
        collection_name: ChromaDB collection name (default "knowledge_base")
    
    Returns:
        JSON string with search results including text snippets and citations
    """
    try:
        if not CHROMADB_AVAILABLE:
            return _fallback_search(query, k)
        
        client = _get_chroma_client()
        if client is None:
            return _fallback_search(query, k)
        
        embedding_model = _get_embedding_model()
        if embedding_model is None:
            return _fallback_search(query, k)
        
        # Get or create collection
        collection = client.get_or_create_collection(collection_name)
        
        # Generate query embedding
        query_embedding = embedding_model.encode([query]).tolist()
        
        # Search the collection
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=k,
            include=["metadatas", "documents", "distances"]
        )
        
        if not results["documents"] or not results["documents"][0]:
            return f"No results found for query: '{query}'"
        
        # Format results
        search_results = []
        for i in range(len(results["documents"][0])):
            result = {
                "rank": i + 1,
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "similarity_score": 1 - results["distances"][0][i],  # Convert distance to similarity
                "citation": _format_citation(results["metadatas"][0][i])
            }
            search_results.append(result)
        
        response = {
            "query": query,
            "total_results": len(search_results),
            "collection": collection_name,
            "results": search_results
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return f"Error in RAG search: {str(e)}"

@tool("search_by_document")
def search_by_document(document_name: str, query: str = None, collection_name: str = "knowledge_base") -> str:
    """
    Search within a specific document or retrieve all content from a document.
    
    Args:
        document_name: Name of the document to search in
        query: Optional search query within the document
        collection_name: ChromaDB collection name
    
    Returns:
        JSON string with document-specific search results
    """
    try:
        if not CHROMADB_AVAILABLE:
            return f"ChromaDB not available. Cannot search document: {document_name}"
        
        client = _get_chroma_client()
        if client is None:
            return "Could not connect to knowledge base"
        
        collection = client.get_or_create_collection(collection_name)
        
        if query:
            # Semantic search within specific document
            embedding_model = _get_embedding_model()
            if embedding_model is None:
                return "Embedding model not available"
            
            query_embedding = embedding_model.encode([query]).tolist()
            
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=10,
                where={"title": document_name},
                include=["metadatas", "documents", "distances"]
            )
        else:
            # Retrieve all content from document
            results = collection.get(
                where={"title": document_name},
                include=["metadatas", "documents"]
            )
            # Convert to query format for consistent processing
            if results["documents"]:
                results = {
                    "documents": [results["documents"]],
                    "metadatas": [results["metadatas"]],
                    "distances": [[0.0] * len(results["documents"])]  # Dummy distances
                }
            else:
                results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        
        if not results["documents"] or not results["documents"][0]:
            return f"No content found in document '{document_name}'" + (f" for query '{query}'" if query else "")
        
        # Format results
        document_results = []
        for i in range(len(results["documents"][0])):
            result = {
                "section": i + 1,
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "citation": _format_citation(results["metadatas"][0][i])
            }
            if query:  # Add similarity score for search results
                result["similarity_score"] = 1 - results["distances"][0][i]
            
            document_results.append(result)
        
        response = {
            "document_name": document_name,
            "search_query": query,
            "sections_found": len(document_results),
            "content": document_results
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return f"Error searching document: {str(e)}"

@tool("list_knowledge_sources")
def list_knowledge_sources(collection_name: str = "knowledge_base") -> str:
    """
    List all available documents in the knowledge base.
    
    Args:
        collection_name: ChromaDB collection name
    
    Returns:
        JSON string with available documents and their metadata
    """
    try:
        if not CHROMADB_AVAILABLE:
            return _list_files_fallback()
        
        client = _get_chroma_client()
        if client is None:
            return _list_files_fallback()
        
        collection = client.get_or_create_collection(collection_name)
        
        # Get all documents
        all_docs = collection.get(include=["metadatas"])
        
        if not all_docs["metadatas"]:
            return "No documents found in knowledge base"
        
        # Group by document title
        documents = {}
        for metadata in all_docs["metadatas"]:
            title = metadata.get("title", "unknown")
            if title not in documents:
                documents[title] = {
                    "title": title,
                    "sections": 0,
                    "path": metadata.get("path", "unknown"),
                    "section_names": []
                }
            documents[title]["sections"] += 1
            section = metadata.get("section", "unknown")
            if section not in documents[title]["section_names"]:
                documents[title]["section_names"].append(section)
        
        response = {
            "collection": collection_name,
            "total_documents": len(documents),
            "total_sections": len(all_docs["metadatas"]),
            "documents": list(documents.values())
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return f"Error listing knowledge sources: {str(e)}"

@tool("search_citations")
def search_citations(citation_pattern: str, collection_name: str = "knowledge_base") -> str:
    """
    Search for specific citation patterns or legal references.
    
    Args:
        citation_pattern: Citation pattern to search for (e.g., "bankruptcy", "segregation")
        collection_name: ChromaDB collection name
    
    Returns:
        JSON string with documents containing the citation pattern
    """
    try:
        # This is a text-based search for citation patterns
        if not CHROMADB_AVAILABLE:
            return f"ChromaDB not available. Cannot search citations for: {citation_pattern}"
        
        client = _get_chroma_client()
        if client is None:
            return "Could not connect to knowledge base"
        
        collection = client.get_or_create_collection(collection_name)
        
        # Get all documents and search within text
        all_docs = collection.get(include=["metadatas", "documents"])
        
        if not all_docs["documents"]:
            return "No documents found in knowledge base"
        
        # Search for pattern in document text
        matching_results = []
        for i, (doc, metadata) in enumerate(zip(all_docs["documents"], all_docs["metadatas"])):
            if citation_pattern.lower() in doc.lower():
                # Extract context around the pattern
                context = _extract_context(doc, citation_pattern)
                matching_results.append({
                    "document": metadata.get("title", "unknown"),
                    "section": metadata.get("section", "unknown"),
                    "path": metadata.get("path", "unknown"),
                    "context": context,
                    "citation": _format_citation(metadata)
                })
        
        if not matching_results:
            return f"No citations found matching pattern: '{citation_pattern}'"
        
        response = {
            "search_pattern": citation_pattern,
            "matches_found": len(matching_results),
            "citations": matching_results
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return f"Error searching citations: {str(e)}"

def _format_citation(metadata: Dict[str, Any]) -> str:
    """Format metadata into a proper citation."""
    title = metadata.get("title", "unknown")
    section = metadata.get("section", "")
    path = metadata.get("path", "")
    
    if section and section != "n/a":
        return f"[{path}:{section}]"
    else:
        return f"[{path}]"

def _extract_context(text: str, pattern: str, context_size: int = 100) -> str:
    """Extract context around a search pattern."""
    pattern_lower = pattern.lower()
    text_lower = text.lower()
    
    match_pos = text_lower.find(pattern_lower)
    if match_pos == -1:
        return text[:200] + "..." if len(text) > 200 else text
    
    start = max(0, match_pos - context_size)
    end = min(len(text), match_pos + len(pattern) + context_size)
    
    context = text[start:end]
    if start > 0:
        context = "..." + context
    if end < len(text):
        context = context + "..."
    
    return context

def _fallback_search(query: str, k: int) -> str:
    """Fallback search using simple text matching when ChromaDB is not available."""
    try:
        results = []
        result_count = 0
        
        # Search through knowledge directories
        for knowledge_dir in KNOWLEDGE_DIRS:
            dir_path = PROJECT_ROOT / knowledge_dir
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.rglob("*.md"):
                if result_count >= k:
                    break
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Simple text search
                    if query.lower() in content.lower():
                        context = _extract_context(content, query)
                        results.append({
                            "rank": result_count + 1,
                            "text": context,
                            "metadata": {
                                "title": file_path.name,
                                "path": str(file_path.relative_to(PROJECT_ROOT))
                            },
                            "citation": f"[{file_path.relative_to(PROJECT_ROOT)}]",
                            "similarity_score": 0.5  # Placeholder score
                        })
                        result_count += 1
                
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue
        
        if not results:
            return f"No results found for query: '{query}' (using fallback search)"
        
        response = {
            "query": query,
            "total_results": len(results),
            "collection": "fallback_search",
            "note": "Using fallback text search - ChromaDB not available",
            "results": results
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return f"Error in fallback search: {str(e)}"

def _list_files_fallback() -> str:
    """Fallback method to list knowledge files when ChromaDB is not available."""
    try:
        documents = {}
        
        for knowledge_dir in KNOWLEDGE_DIRS:
            dir_path = PROJECT_ROOT / knowledge_dir
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.rglob("*"):
                if file_path.is_file() and file_path.suffix in [".md", ".txt", ".yaml", ".csv"]:
                    rel_path = str(file_path.relative_to(PROJECT_ROOT))
                    documents[file_path.name] = {
                        "title": file_path.name,
                        "path": rel_path,
                        "type": file_path.suffix[1:],  # Remove the dot
                        "size_bytes": file_path.stat().st_size
                    }
        
        response = {
            "collection": "file_system",
            "total_documents": len(documents),
            "note": "Using file system listing - ChromaDB not available",
            "documents": list(documents.values())
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return f"Error listing files: {str(e)}"

if __name__ == "__main__":
    # Test the tools
    print("Testing RAG Search Tools:")
    
    print("\n1. Basic search for 'asset tracing':")
    print(rag_search("asset tracing", k=3))
    
    print("\n2. List knowledge sources:")
    print(list_knowledge_sources())
    
    print("\n3. Search citations for 'bankruptcy':")
    print(search_citations("bankruptcy"))
    
    print("\n4. Search in specific document:")
    print(search_by_document("bankruptcy_basics.md", "segregation"))


