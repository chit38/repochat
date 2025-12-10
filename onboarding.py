from ingestion import ingestion 
from processing import UniversalChunker, VectorStore
from configparser import ConfigParser
import json
import os
from datetime import datetime

class RepoOnboarder():

    def __init__(self):
        configur = ConfigParser()
        configur.read('config.ini')
        self.embedding_model = configur['config'].get('emebdding_model')
        self.registry_file = configur['files'].get('registry_file')
        self.registry = self._load_registry()
        
    def _load_registry(self):
        """Load existing registry or create new one"""
        if os.path.exists(self.registry_file):
            #print('True')
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_registry(self):
        """Save registry to file"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def _add_to_registry(self, repo_url, repo_name, repo_path, collection_path):
        """Add new repo entry to registry"""
        self.registry[repo_name] = {
            "url": repo_url,
            "collection_name": repo_name,
            "local_path": repo_path,
            "collection_path": collection_path,
            "processed_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "Embedded"
        }
        self._save_registry()
    
    def is_repo_processed(self, repo_url):
        """Check if repo is already processed"""
        for repo_name, info in self.registry.items():
            #print(repo_name)
            if info['url'] == repo_url:
                return True, repo_name, info
        return False, None, None
    
    def ingest_repo(self, repo_url):
        ingestor = ingestion(repo_url)
        self.repo_name = ingestor.repo_name
        self.repo_path = ingestor.dest_path
        ingestor.ingest()
        
        return self.repo_name, self.repo_path

    def process_repo(self):
        chunker = UniversalChunker()
        print("Chunking all files in a directory recursively")
        chunks = chunker.chunk_directory(self.repo_path)
        print("Chunking completed")

        collection_path = 'chromadb/' + self.repo_name
        store = VectorStore(
            collection_name=self.repo_name, 
            persist_directory=collection_path, 
            embedding_model=self.embedding_model
        )
        store.add_chunks(chunks)
        stats = store.get_collection_stats()
        print(f"\nCollection stats: {stats}")

        return collection_path
    
    def onboard(self, repo_url):
        # Check if repo already processed
        is_processed, repo_name, repo_info = self.is_repo_processed(repo_url)
        
        if is_processed:
            print(f"\n✓ Repo '{repo_name}' already processed!")
            print(f"  Collection: {repo_info['collection_name']}")
            print(f"  Processed on: {repo_info['processed_date']}")
            print(f"  Status: {repo_info['status']}")
            print("\nSkipping ingestion and processing...\n")
            return repo_info
        
        # Process new repo
        #print(f"\nProcessing new repo: {repo_url}\n")
        self.repo_name, self.repo_path = self.ingest_repo(repo_url)
        collection_path = self.process_repo()
        
        # Add to registry
        self._add_to_registry(repo_url, self.repo_name, self.repo_path, collection_path)
        print(f"\n✓ Repo '{self.repo_name}' added to registry!\n")
        
        return self.registry[self.repo_name]


if __name__ == "__main__":
    repo_url = input('Please enter github repo link: ')
    onboarder = RepoOnboarder()
    repo_info = onboarder.onboard(repo_url)