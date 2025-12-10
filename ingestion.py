import git
import os
import hashlib
from datetime import datetime, timezone
import json

class ingestion():
    def __init__(self, repo_url):
        if os.getcwd().split('\\')[-1] == 'ingestion':
            self.root = os.path.abspath('..').replace('\\', '/')
        else:
            self.root = os.path.abspath('.').replace('\\', '/')
        self.repo_url = repo_url 
        self.repo_name = repo_url.split('/')[-1]
        print(f"Repo_name: {self.repo_name}")
        self.dest_path = self.root + "/data/" + self.repo_name + '/repo'

        self.EXTENSION_TO_LANGUAGE = {
            ".py": "python",
            ".java": "java",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c/c++ header",
            ".hpp": "cpp",
            ".go": "go",
            ".rs": "rust",
            ".sh": "shell",
            ".md": "markdown",
            ".txt": "text",
            ".json": "json",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".html": "html",
            ".css": "css",
            ".R": "R",
            ".ipynb": "jupyter",
            # add more as needed
        }

    def clone_repo(self, repo_url):
        try:
            git.Repo.clone_from(repo_url, self.dest_path)
            print(f"Repository successfully cloned to: {self.dest_path}")
        except git.exc.GitCommandError as e:
            print(f"Error cloning repository: {e}")
    
    def scan_files(self,exclude_dirs = {'node_modules', '.git', 'dist', 'build', '__pycache__', 'venv', '.venv'}):
        results = []
        for root, dirs, files in os.walk(self.dest_path):
            # prune excluded dirs
            #print(root, dirs, files)
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for fname in files:
                full = root + '/' + fname
                results.append(full)
            #print(results)
        return results
    
    def compute_sha256(self, path, chunk_size= 8192):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()


    def is_binary_file(self, path, sample_size = 1024):
        """Rudimentary binary detection: checks for null bytes in the first bytes."""
        try:
            with open(path, "rb") as f:
                sample = f.read(sample_size)
                if b"\x00" in sample:
                    return True
                # heuristic: high proportion of non-text bytes
                text_chars = bytes(range(32, 127)) + b"\n\r\t\b"
                nontext = sum(1 for b in sample if b not in text_chars)
                if sample and (nontext / len(sample)) > 0.30:
                    return True
        except (PermissionError, OSError):
            # treat unreadable files as binary to avoid reading them
            return True
        return False

    def get_language_from_extension(self, path):
        _, ext = os.path.splitext(path.lower())
        return self.EXTENSION_TO_LANGUAGE.get(ext)


    def count_lines(self, path):
        try:
            with open(path, "rb") as f:
                return sum(1 for _ in f)
        except Exception:
            return None


    def extract_metadata(self):
        file_list = self.file_list
        metadata_list = []
        for file in file_list:
            sha256 = self.compute_sha256(file)
            is_binary = self.is_binary_file(file)
            extension = self.get_language_from_extension(file)
            num__lines = self.count_lines(file)
            rel_path = os.path.relpath(file, self.root).replace('\\', '/')

            metadata_list.append({
                "filename": file.split('/')[-1],
                "path": rel_path,
                "sha256": sha256,
                "is_binary": is_binary,
                "language": extension,
                "line_count": num__lines
            })
        return metadata_list
    
    def save_metadata(self):
        #os.makedirs(self.dest_path.split('repo')[0] + 'metadata', exist_ok = True)
        output_path = self.dest_path.split('repo')[0] + 'metadata.json'
        print(f"Saving metadata at {output_path}")
        with open(output_path , "w", encoding="utf-8") as fh:
            json.dump(list(self.metadata_list), fh, ensure_ascii=False, indent=2)

    def ingest(self):
        print(f'Cloning {self.repo_name}')
        self.clone_repo(self.repo_url)
        print('Scanning files')
        self.file_list = self.scan_files()
        print(f'Scanning files completed. Total {len(self.file_list)} files found')
        print('Extracting metadata for all files')
        self.metadata_list = self.extract_metadata()
        print("extraction of metadata completed")
        self.save_metadata()

if __name__ == "__main__":
    # This code only runs when script is executed directly
    print("Please enter repo URL > ")
    repo_url = input()
    reop_name = ingestion(repo_url)
    print("If name of repo correct, Press 'Y' to run ingestion pipeline or else 'n: ")
    if input() in ['Y','y', 'Yes','yes']:
        reop_name.ingest()
    else:
        exit() 