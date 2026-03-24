import os
import fitz  # PyMuPDF
import docx
import chromadb
from sentence_transformers import SentenceTransformer

# Initialize model once
model = SentenceTransformer('all-MiniLM-L6-v2')

class ContextHarvester:
    def __init__(self, chroma_client=None):
        self.chroma_client = chroma_client or chromadb.EphemeralClient()

    def process_file(self, filepath: str, session_id: str):
        collection_name = f"session_{session_id}"
        collection = self.chroma_client.get_or_create_collection(name=collection_name)

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
            ids = [f"{filename}_{i}" for i in range(len(chunks))]
            
            # Embed
            embeddings = model.encode(texts).tolist()
            
            # Add to chroma
            collection.add(
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

    def get_collection(self, session_id: str):
        collection_name = f"session_{session_id}"
        try:
            return self.chroma_client.get_collection(name=collection_name)
        except:
            return None
