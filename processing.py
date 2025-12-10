import os
import ast
import json
import re
from pathlib import Path
from typing import List, Dict
import chromadb
from sentence_transformers import SentenceTransformer
import hashlib
from configparser import ConfigParser

# Python AST Chunker (from previous code)
def get_chunk_size(code):
    return len(code) // 4

def extract_code_segment(lines, start, end):
    return "\n".join(lines[start:end])

def split_large_class(node, code_lines, max_tokens=500):
    chunks = []
    class_start = node.lineno - 1
    header_end = class_start + 1
    
    for item in node.body:
        if not isinstance(item, ast.Expr) or not isinstance(item.value, ast.Constant):
            header_end = item.lineno - 1
            break
    
    header = extract_code_segment(code_lines, class_start, header_end)

    current_chunk = header
    current_start = class_start + 1
    current_end = header_end
    
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_start = item.lineno - 1
            method_end = item.end_lineno
            method_code = extract_code_segment(code_lines, method_start, method_end)
            
            test_chunk = current_chunk + "\n" + method_code
            if get_chunk_size(test_chunk) > max_tokens and current_chunk.strip():
                chunks.append({
                    "content": current_chunk,
                    "start_line": current_start,
                    "end_line": current_end,
                    "chunk_type": "class_part",
                    "name": node.name
                })
                current_chunk = header + "\n    # ... (continued)\n" + method_code
                current_start = method_start + 1
                current_end = method_end
            else:
                current_chunk = test_chunk
                current_end = method_end
    
    if current_chunk.strip():
        chunks.append({
            "content": current_chunk,
            "start_line": current_start,
            "end_line": current_end,
            "chunk_type": "class_part" if len(chunks) > 0 else "class",
            "name": node.name
        })
    
    return chunks

def chunk_python_code(code, max_tokens=500):
    chunks = []
    lines = code.split("\n")
    
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return [{"content": code, "start_line": 1, "end_line": len(lines), "chunk_type": "full_file"}]
    
    covered_lines = set()
    
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            chunk_code = extract_code_segment(lines, start_line, end_line)
            
            for i in range(start_line, end_line):
                covered_lines.add(i)
            
            if get_chunk_size(chunk_code) > max_tokens:
                if isinstance(node, ast.ClassDef):
                    sub_chunks = split_large_class(node, lines, max_tokens)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append({
                        "content": chunk_code,
                        "start_line": start_line + 1,
                        "end_line": end_line,
                        "chunk_type": "function",
                        "name": node.name
                    })
            else:
                chunk_type = "class" if isinstance(node, ast.ClassDef) else "function"
                chunks.append({
                    "content": chunk_code,
                    "start_line": start_line + 1,
                    "end_line": end_line,
                    "chunk_type": chunk_type,
                    "name": node.name
                })
    
    leftover_lines = [line for i, line in enumerate(lines) if i not in covered_lines]
    if leftover_lines:
        chunks.append({
            "content": "\n".join(leftover_lines),
            "start_line": 1,
            "end_line": len(lines),
            "chunk_type": "top_level"
        })
    
    return chunks


# Markdown Chunker
def chunk_markdown(content, max_tokens=500):
    chunks = []
    sections = re.split(r'\n(?=#{1,6} )', content)
    
    current_line = 1  # Track line number
    
    for section in sections:
        section_lines = section.split('\n')
        start_line = current_line
        end_line = current_line + len(section_lines) - 1
        
        if get_chunk_size(section) > max_tokens:
            paragraphs = section.split('\n\n')
            para_line = start_line
            current_chunk = ""
            chunk_start = para_line
            
            for para in paragraphs:
                para_lines = len(para.split('\n'))
                if get_chunk_size(current_chunk + para) > max_tokens and current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "chunk_type": "markdown_section",
                        "start_line": chunk_start,
                        "end_line": para_line - 1
                    })
                    current_chunk = para
                    chunk_start = para_line
                else:
                    current_chunk += "\n\n" + para if current_chunk else para
                para_line += para_lines
            
            if current_chunk.strip():
                chunks.append({
                    "content": current_chunk.strip(),
                    "chunk_type": "markdown_section",
                    "start_line": chunk_start,
                    "end_line": end_line
                })
        else:
            chunks.append({
                "content": section.strip(),
                "chunk_type": "markdown_section",
                "start_line": start_line,
                "end_line": end_line
            })
        
        current_line = end_line + 1
    
    return chunks


# JSON Chunker
def chunk_json(content, max_tokens=500):
    try:
        data = json.loads(content)
        chunks = []
        lines = content.split('\n')
        
        if isinstance(data, dict):
            current_line = 1
            for key, value in data.items():
                chunk_content = json.dumps({key: value}, indent=2)
                chunk_lines = len(chunk_content.split('\n'))
                chunks.append({
                    "content": chunk_content,
                    "chunk_type": "json_key",
                    "name": key,
                    "start_line": current_line,
                    "end_line": current_line + chunk_lines - 1
                })
                current_line += chunk_lines
                
        elif isinstance(data, list):
            current_line = 1
            for i, item in enumerate(data):
                chunk_content = json.dumps(item, indent=2)
                chunk_lines = len(chunk_content.split('\n'))
                chunks.append({
                    "content": chunk_content,
                    "chunk_type": "json_array_item",
                    "name": f"item_{i}",
                    "start_line": current_line,
                    "end_line": current_line + chunk_lines - 1
                })
                current_line += chunk_lines
        else:
            chunks.append({
                "content": content,
                "chunk_type": "json_full",
                "start_line": 1,
                "end_line": len(lines)
            })
        
        return chunks
    except json.JSONDecodeError:
        return [{
            "content": content,
            "chunk_type": "json_invalid",
            "start_line": 1,
            "end_line": len(content.split('\n'))
        }]

# Generic Text Chunker
def chunk_text(content, max_tokens=500):
    chunks = []
    paragraphs = content.split('\n\n')
    current_chunk = ""
    current_line = 1
    chunk_start_line = 1
    
    for para in paragraphs:
        para_lines = len(para.split('\n'))
        
        if get_chunk_size(current_chunk + para) > max_tokens and current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "chunk_type": "text_chunk",
                "start_line": chunk_start_line,
                "end_line": current_line - 1
            })
            current_chunk = para
            chunk_start_line = current_line
        else:
            current_chunk += "\n\n" + para if current_chunk else para
        
        current_line += para_lines + 2  # +2 for \n\n separator
    
    if current_chunk.strip():
        chunks.append({
            "content": current_chunk.strip(),
            "chunk_type": "text_chunk",
            "start_line": chunk_start_line,
            "end_line": current_line - 1
        })
    
    return chunks


# Line-based Chunker (fallback)
def chunk_by_lines(content, max_tokens=500):
    lines = content.split('\n')
    chunks = []
    lines_per_chunk = max(10, max_tokens // 20)  # Rough estimate
    
    for i in range(0, len(lines), lines_per_chunk):
        chunk_lines = lines[i:i + lines_per_chunk]
        chunks.append({
            "content": "\n".join(chunk_lines),
            "start_line": i + 1,
            "end_line": min(i + lines_per_chunk, len(lines)),
            "chunk_type": "line_based"
        })
    
    return chunks


# Main Router
class UniversalChunker:
    # Files to skip
    SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.tar', '.gz', '.exe', '.bin'}
    SKIP_DIRS = {'node_modules', '.git', 'dist', 'build', '__pycache__', 'venv', '.venv'}
    
    def __init__(self, max_tokens=500):
        self.max_tokens = max_tokens
        if os.getcwd().split('\\')[-1] == 'processing':
            self.root = os.path.abspath('..').replace('\\', '/')
        else:
            self.root = os.path.abspath('.').replace('\\', '/')
    
    def should_skip(self, file_path):
        path = Path(file_path)
        
        # Skip by directory
        if any(skip_dir in path.parts for skip_dir in self.SKIP_DIRS):
            return True
        
        # Skip by extension
        if path.suffix.lower() in self.SKIP_EXTENSIONS:
            return True
        
        return False
    
    def chunk_file(self, file_path: str, org_metadata) -> List[Dict]:
        """Main entry point to chunk any file"""
        if self.should_skip(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError):
            return []
        
        file_ext = Path(file_path).suffix.lower()
        
        # Route to appropriate chunker
        if file_ext == '.py':
            chunks = chunk_python_code(content, self.max_tokens)
        elif file_ext in {'.md', '.markdown'}:
            chunks = chunk_markdown(content, self.max_tokens)
        elif file_ext == '.json':
            chunks = chunk_json(content, self.max_tokens)
        elif file_ext in {'.txt', '.log', '.rst'}:
            chunks = chunk_text(content, self.max_tokens)
        elif file_ext in {'.js', '.ts', '.java', '.go', '.rs', '.rb', '.php', '.c', '.cpp', '.h'}:
            # Fallback for code files (replace with tree-sitter if needed)
            chunks = chunk_by_lines(content, self.max_tokens)
        else:
            chunks = chunk_text(content, self.max_tokens)
        
        # Add file metadata to each chunk
        for chunk in chunks:
            chunk['file_path'] = org_metadata['path']
            chunk['file_name'] = Path(file_path).name
            chunk['file_extension'] = file_ext
            chunk['language'] = self._detect_language(file_ext)
            chunk['og_meta'] = org_metadata
        
        return chunks
    
    def chunk_directory(self, dir_path: str) -> List[Dict]:
        """Chunk all files in a directory recursively"""
        all_chunks = []

        with open(dir_path.split('repo')[0] + '/metadata.json') as f:
            file_list = json.load(f)
        for file in file_list:
            chunks = self.chunk_file(self.root + '/'+ file['path'], file)
            
        
        # for root, dirs, files in os.walk(dir_path):
        #     # Filter out skip directories
        #     dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            
        #     for file in files:
        #         file_path = root + '/' + file
        #         chunks = self.chunk_file(file_path)
            all_chunks.extend(chunks)
        
        return all_chunks
                
    
    def _detect_language(self, ext):
        lang_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.java': 'java', '.go': 'go', '.rs': 'rust', '.rb': 'ruby',
            '.php': 'php', '.c': 'c', '.cpp': 'cpp', '.h': 'c',
            '.md': 'markdown', '.json': 'json', '.txt': 'text'
        }
        return lang_map.get(ext, 'unknown')

class VectorStore:
    def __init__(self, collection_name, persist_directory, embedding_model):
        """Initialize embedding model and ChromaDB client"""
        # Load embedding model
        self.model = SentenceTransformer(embedding_model)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
        )
    
    def _generate_id(self, chunk) -> str:
        """Generate unique ID for chunk"""
        unique_string = f"{chunk['file_path']}_{chunk.get('start_line', 0)}_{chunk.get('end_line', 0)}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def add_chunks(self, chunks):
        """Embed and store chunks in ChromaDB"""
        if not chunks:
            return
        
        # Prepare data
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            # Generate unique ID
            chunk_id = self._generate_id(chunk)
            ids.append(chunk_id)
            
            # Content to embed
            documents.append(chunk['content'])
            
            # Metadata (everything except content)
            metadata = {
                'file_path': chunk['file_path'],
                'file_name': chunk['file_name'],
                'file_extension': chunk['file_extension'],
                'language': chunk['language'],
                'chunk_type': chunk['chunk_type'],
                #'og_meta':chunk['og_meta']
            }
            
            # Add optional fields
            if 'name' in chunk:
                metadata['name'] = chunk['name']
            if 'start_line' in chunk:
                metadata['start_line'] = chunk['start_line']
            if 'end_line' in chunk:
                metadata['end_line'] = chunk['end_line']
            
            metadatas.append(metadata)
        
        # Generate embeddings
        print(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = self.model.encode(documents, show_progress_bar=True)
        
        # Store in ChromaDB
        print("Storing in ChromaDB...")
        self.collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=documents,
            metadatas=metadatas
        )
        
        print(f"✓ Stored {len(chunks)} chunks")
    
    def search(self, query: str, n_results=5, filters=None):
        """Search for similar code chunks"""
        # Generate query embedding
        query_embedding = self.model.encode([query])[0]
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=filters  # e.g., {"language": "python"}
        )
        
        return results
    
    
    def get_collection_stats(self):
        """Get statistics about stored chunks"""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": self.collection.name
        }
    
    
if __name__ == "__main__":
    print('Please enter repo path')
    repo_path = input()
    chunker = UniversalChunker(max_tokens=200)
    chunks = chunker.chunk_directory(repo_path)

    configur = ConfigParser()
    configur.read('config.ini')

    embedding_model = configur['config'].get('emebdding_model')
    store = VectorStore(collection_name="my_repo", persist_directory='test_db', embedding_model = embedding_model)
    store.add_chunks(chunks[:100])
    stats = store.get_collection_stats()
    print(f"\nCollection stats: {stats}")

    print(len(chunks))
