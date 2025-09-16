#!/usr/bin/env python3
"""
Initialize ChromaDB with knowledge base documents.
This script needs to be run once to populate the RAG database.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from chromadb import PersistentClient
    from sentence_transformers import SentenceTransformer
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"❌ Dependencies not available: {e}")
    print("Please install: pip install chromadb sentence-transformers")
    DEPENDENCIES_AVAILABLE = False
    sys.exit(1)

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = PROJECT_ROOT / ".chroma"
KNOWLEDGE_DIRS = ["knowledge", "policies", "catalogs"]
COLLECTION_NAME = "knowledge_base"

def chunk_document(content: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split document into overlapping chunks for better semantic search."""
    if len(content) <= chunk_size:
        return [content]
    
    chunks = []
    start = 0
    
    while start < len(content):
        end = start + chunk_size
        
        # Try to break at sentence boundaries
        if end < len(content):
            # Look for sentence endings within the last 100 characters
            last_period = content.rfind('.', end - 100, end)
            last_newline = content.rfind('\n\n', end - 100, end)
            
            best_break = max(last_period, last_newline)
            if best_break > start:
                end = best_break + 1
        
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
    
    return chunks

def extract_sections(content: str, file_path: Path) -> List[Dict[str, Any]]:
    """Extract sections from markdown content."""
    sections = []
    lines = content.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        if line.startswith('#'):
            # Save previous section
            if current_section and current_content:
                section_content = '\n'.join(current_content).strip()
                if section_content:
                    chunks = chunk_document(section_content)
                    for i, chunk in enumerate(chunks):
                        sections.append({
                            'title': file_path.name,
                            'section': current_section,
                            'chunk_id': i,
                            'content': chunk,
                            'path': str(file_path.relative_to(PROJECT_ROOT)),
                            'metadata': {
                                'title': file_path.name,
                                'section': current_section,
                                'chunk_id': i,
                                'path': str(file_path.relative_to(PROJECT_ROOT)),
                                'file_type': 'markdown'
                            }
                        })
            
            # Start new section
            current_section = line.strip('# ').strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Handle last section
    if current_section and current_content:
        section_content = '\n'.join(current_content).strip()
        if section_content:
            chunks = chunk_document(section_content)
            for i, chunk in enumerate(chunks):
                sections.append({
                    'title': file_path.name,
                    'section': current_section,
                    'chunk_id': i,
                    'content': chunk,
                    'path': str(file_path.relative_to(PROJECT_ROOT)),
                    'metadata': {
                        'title': file_path.name,
                        'section': current_section,
                        'chunk_id': i,
                        'path': str(file_path.relative_to(PROJECT_ROOT)),
                        'file_type': 'markdown'
                    }
                })
    
    return sections

def process_yaml_file(file_path: Path) -> List[Dict[str, Any]]:
    """Process YAML files as structured documents."""
    try:
        import yaml
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            yaml_data = yaml.safe_load(content)
        
        # Convert YAML to searchable text
        text_content = f"# {file_path.name}\n\n"
        text_content += json.dumps(yaml_data, indent=2)
        
        chunks = chunk_document(text_content)
        sections = []
        
        for i, chunk in enumerate(chunks):
            sections.append({
                'title': file_path.name,
                'section': f'section_{i}',
                'chunk_id': i,
                'content': chunk,
                'path': str(file_path.relative_to(PROJECT_ROOT)),
                'metadata': {
                    'title': file_path.name,
                    'section': f'section_{i}',
                    'chunk_id': i,
                    'path': str(file_path.relative_to(PROJECT_ROOT)),
                    'file_type': 'yaml'
                }
            })
        
        return sections
        
    except Exception as e:
        print(f"⚠️  Error processing YAML file {file_path}: {e}")
        return []

def initialize_knowledge_base():
    """Initialize ChromaDB with knowledge base documents."""
    print("🚀 Initializing RAG Knowledge Base")
    print("=" * 50)
    
    if not DEPENDENCIES_AVAILABLE:
        return False
    
    # Initialize ChromaDB
    print("📦 Setting up ChromaDB...")
    CHROMA_DIR.mkdir(exist_ok=True)
    client = PersistentClient(path=str(CHROMA_DIR))
    
    # Delete existing collection if it exists
    try:
        existing_collections = [c.name for c in client.list_collections()]
        if COLLECTION_NAME in existing_collections:
            print(f"🗑️  Deleting existing collection: {COLLECTION_NAME}")
            client.delete_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"⚠️  Note: {e}")
    
    # Create new collection
    collection = client.create_collection(COLLECTION_NAME)
    print(f"✅ Created collection: {COLLECTION_NAME}")
    
    # Initialize embedding model
    print("🤖 Loading embedding model...")
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    print("✅ Embedding model loaded")
    
    # Process all knowledge documents
    all_documents = []
    all_embeddings = []
    all_metadatas = []
    all_ids = []
    
    total_files = 0
    processed_files = 0
    
    for knowledge_dir in KNOWLEDGE_DIRS:
        dir_path = PROJECT_ROOT / knowledge_dir
        
        print(f"\n📁 Processing directory: {knowledge_dir}/")
        
        if not dir_path.exists():
            print(f"   ⚠️  Directory not found: {dir_path}")
            continue
        
        # Process markdown files
        md_files = list(dir_path.rglob("*.md"))
        yaml_files = list(dir_path.rglob("*.yaml")) + list(dir_path.rglob("*.yml"))
        
        all_files = md_files + yaml_files
        total_files += len(all_files)
        
        for file_path in all_files:
            print(f"   📄 Processing: {file_path.name}")
            
            try:
                if file_path.suffix.lower() in ['.md']:
                    # Process markdown
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    sections = extract_sections(content, file_path)
                    
                elif file_path.suffix.lower() in ['.yaml', '.yml']:
                    # Process YAML
                    sections = process_yaml_file(file_path)
                    
                else:
                    continue
                
                for section in sections:
                    # Generate embedding
                    embedding = embedding_model.encode([section['content']])[0].tolist()
                    
                    # Create unique ID
                    doc_id = f"{file_path.stem}_{section['section']}_{section['chunk_id']}"
                    
                    all_documents.append(section['content'])
                    all_embeddings.append(embedding)
                    all_metadatas.append(section['metadata'])
                    all_ids.append(doc_id)
                
                processed_files += 1
                print(f"      ✅ Added {len(sections)} chunks")
                
            except Exception as e:
                print(f"      ❌ Error processing {file_path}: {e}")
    
    # Add all documents to ChromaDB
    if all_documents:
        print(f"\n💾 Adding {len(all_documents)} document chunks to database...")
        
        # Add in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(all_documents), batch_size):
            end_idx = min(i + batch_size, len(all_documents))
            
            collection.add(
                ids=all_ids[i:end_idx],
                embeddings=all_embeddings[i:end_idx],
                documents=all_documents[i:end_idx],
                metadatas=all_metadatas[i:end_idx]
            )
            
            print(f"   📦 Added batch {i//batch_size + 1} ({end_idx - i} chunks)")
        
        print("✅ All documents added successfully!")
    else:
        print("❌ No documents found to add!")
        return False
    
    # Verify the database
    print(f"\n🧪 Verifying database...")
    test_results = collection.query(
        query_texts=["asset segregation"],
        n_results=3
    )
    
    if test_results['documents'] and test_results['documents'][0]:
        print("✅ Database verification successful!")
        print(f"   Found {len(test_results['documents'][0])} test results")
        print(f"   Sample result: {test_results['documents'][0][0][:100]}...")
    else:
        print("⚠️  Database verification failed - no search results")
    
    print("\n" + "=" * 50)
    print("🎉 RAG Knowledge Base Initialization Complete!")
    print(f"📊 Summary:")
    print(f"   • Files processed: {processed_files}/{total_files}")
    print(f"   • Document chunks: {len(all_documents)}")
    print(f"   • Database location: {CHROMA_DIR}")
    print(f"   • Collection name: {COLLECTION_NAME}")
    print()
    print("🚀 RAG search is now ready to use!")
    
    return True

if __name__ == "__main__":
    success = initialize_knowledge_base()
    sys.exit(0 if success else 1)
