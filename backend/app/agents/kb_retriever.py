import os
import fitz  # PyMuPDF
import docx
try:
    import chromadb
except ImportError:
    chromadb = None
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
except ImportError:
    model = None
from typing import List, Dict, Any

class KBRetrieverAgent:
    def __init__(self, chroma_client):
        self.chroma_client = chroma_client
        self.collection_name = "tracelight_kb"
        self.collection = self.chroma_client.get_or_create_collection(name=self.collection_name)

    def process_file(self, filepath: str, doc_type: str, description: str):
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()

        text_content = ""
        chunks = []
        if ext == ".pdf":
            doc = fitz.open(filepath)
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                chunks.extend(self._chunk_text(page_text, filename, page_num + 1))
        elif ext == ".docx":
            doc = docx.Document(filepath)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            text_content = "\n".join(full_text)
            chunks.extend(self._chunk_text(text_content, filename, 1))
        elif ext == ".txt":
            with open(filepath, 'r') as f:
                text_content = f.read()
            chunks.extend(self._chunk_text(text_content, filename, 1))
        else:
            return  # unsupported

        if chunks:
            texts = [c["text"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]
            # Add doc_type and description to metadata
            for m in metadatas:
                m["doc_type"] = doc_type
                m["description"] = description
                
            ids = [f"{filename}_{i}" for i in range(len(chunks))]
            
            # Embed
            embeddings = model.encode(texts).tolist()
            
            # Add to chroma
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )

    def _chunk_text(self, text: str, filename: str, page_number: int, chunk_size=500, overlap=50):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            if not chunk_words:
                continue
            chunk_text = " ".join(chunk_words)
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source_filename": filename,
                    "page_number": page_number,
                    "chunk_index": i
                }
            })
        return chunks

    def retrieve_for_question(self, question_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not question_text:
            return []
            
        try:
            query_embedding = model.encode([question_text]).tolist()
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k
            )
            retrieved = []
            
            if results and results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    doc = results["documents"][0][i]
                    meta = results["metadatas"][0][i]
                    distance = results["distances"][0][i] if "distances" in results and results["distances"] else 0
                    
                    # Convert distance to a similarity score (approximate if cosine or L2)
                    # For chroma default L2, smaller distance is better. 
                    # Assuming normalized embeddings, cosine sim = 1 - L2^2 / 2
                    similarity = max(0.0, 1.0 - (distance / 2.0))
                    
                    retrieved.append({
                        "text": doc,
                        "source_filename": meta.get("source_filename", "Unknown"),
                        "page_number": meta.get("page_number", 0),
                        "similarity_score": similarity
                    })
            return retrieved
        except Exception:
            return []
