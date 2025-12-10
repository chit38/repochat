import os
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings, VectorStoreIndex, StorageContext
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.memory import ChatMemoryBuffer
from configparser import ConfigParser
from dotenv import load_dotenv


class RAGChatbot:
    def __init__(self, chroma_path, collection_name, google_api_key=None, config_file='config.ini'):
        """Initialize RAG chatbot with vector store and LLM"""
        
        # Setup ChromaDB
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        vector_store = ChromaVectorStore(self.collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Setup LLM
        llm = GoogleGenAI(
            model="gemini-2.5-flash",
            api_key=os.environ.get("GOOGLE_API_KEY"),
            temperature=0.25,
            max_output_tokens=1024,
            sync_mode=True,
        )
        Settings.llm = llm
        
        # Setup embedding model
        configur = ConfigParser()
        configur.read(config_file)
        embedding_model = configur['config'].get('emebdding_model', 'all-mpnet-base-v2')
        Settings.embed_model = HuggingFaceEmbedding(model_name=embedding_model)
        
        # Create index and query engine with memory
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
        )
        
        # Create chat engine with memory
        self.chat_engine = index.as_chat_engine(
            chat_mode="condense_plus_context",
            memory=ChatMemoryBuffer.from_defaults(token_limit=3000),
            similarity_top_k=5,
            llm=llm
        )
        
        self.chat_history = []
    
    def chat(self, message):
        """Send a message and get response"""
        response = self.chat_engine.chat(message)
        
        # Store in history
        self.chat_history.append({
            "user": message,
            "assistant": str(response)
        })
        
        return str(response)
    
    def reset(self):
        """Reset chat memory"""
        self.chat_engine.reset()
        self.chat_history = []
    
    def get_history(self):
        """Get chat history"""
        return self.chat_history
    
    def start_chat(self):
        """Start interactive chat session"""
        print("RAG Chatbot initialized! Type 'bye', 'quit', or 'exit' to stop.\n")
        
        exit_words = ['bye', 'quit', 'exit', 'stop']
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in exit_words:
                print("Goodbye! 👋")
                break
            
            if not user_input:
                continue
            
            response = self.chat(user_input)
            print(f"\nAssistant:\n {response}\n")

# Example usage in script
if __name__ == "__main__":
    # Create chatbot
    load_dotenv()  # Load environment variables from .env
    api_key = os.getenv("GOOGLE_API_KEY")
    os.environ["GOOGLE_API_KEY"] = api_key

    repos = os.listdir('chromadb')
    print("Available repos to chat: ", repos)
    repo_name = input('Please enter repo name: ')

    chroma_path = 'chromadb/' + repo_name

    try:
        chatbot = RAGChatbot(
        chroma_path=chroma_path,
        collection_name=repo_name,
        )
    except Exception as e:
        print(e)

    # Start interactive chat
    chatbot.start_chat()