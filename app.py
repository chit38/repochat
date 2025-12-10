import gradio as gr
import json
import os
from dotenv import load_dotenv
from configparser import ConfigParser
from onboarding import RepoOnboarder
from ragchatbot import RAGChatbot

# Load environment variables
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
os.environ["GOOGLE_API_KEY"] = api_key

# Load config
configur = ConfigParser()
configur.read('config.ini')
registry_file = configur['files'].get('registry_file')

# Global chatbot instance
current_chatbot = None
current_repo = None

def load_registry():
    """Load processed repos from registry"""
    if os.path.exists(registry_file):
        with open(registry_file, 'r') as f:
            return json.load(f)
    return {}

def get_repo_list():
    """Get list of available repos"""
    repos = load_registry()
    return list(repos.keys())

def load_repository(repo_selection, new_repo_url):
    """Load or process repository"""
    global current_chatbot, current_repo
    
    try:
        # Determine which repo to use
        if repo_selection and repo_selection != "-- Add New Repository --":
            repo_name = repo_selection
            status_msg = f"Loading existing repository: {repo_name}"
        elif new_repo_url:
            status_msg = f"Processing new repository: {new_repo_url}\n\nThis may take a few minutes..."
            yield status_msg, gr.update(interactive=False)
            
            # Process new repo
            onboarder = RepoOnboarder()
            repo_info = onboarder.onboard(new_repo_url)
            repo_name = repo_info['collection_name']
            status_msg = f"✓ Repository '{repo_name}' processed successfully!"
        else:
            yield "⚠️ Please select a repository or enter a GitHub URL", gr.update(interactive=True)
            return
        
        # Load chatbot
        chroma_path = f'chromadb/{repo_name}'
        current_chatbot = RAGChatbot(
            chroma_path=chroma_path,
            collection_name=repo_name
        )
        current_repo = repo_name
        
        final_msg = f"✓ Repository '{repo_name}' loaded successfully!\n\nYou can now start chatting below."
        yield final_msg, gr.update(interactive=True)
        
    except Exception as e:
        yield f"❌ Error: {str(e)}", gr.update(interactive=True)

def chat_fn(message, history):
    """Handle chat messages"""
    global current_chatbot
    
    if current_chatbot is None:
        return "⚠️ Please load a repository first using the panel above."
    
    try:
        response = current_chatbot.chat(message)
        return response
    except Exception as e:
        return f"❌ Error: {str(e)}"

def reset_chat():
    """Reset chat history"""
    global current_chatbot
    if current_chatbot:
        current_chatbot.reset()
    return None

# Build Gradio interface
with gr.Blocks(title="RAG Code Chatbot", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 RAG Code Chatbot")
    gr.Markdown("Chat with your GitHub repositories using AI-powered search")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📚 Repository Selection")
            
            # Dropdown for existing repos
            repo_dropdown = gr.Dropdown(
                choices=["-- Add New Repository --"] + get_repo_list(),
                label="Select Existing Repository",
                value=None
            )
            
            # Textbox for new repo
            new_repo_input = gr.Textbox(
                label="Or Enter New GitHub Repository URL",
                placeholder="https://github.com/user/repo",
                lines=1
            )
            
            # Load button
            load_btn = gr.Button("Load Repository", variant="primary")
            
            # Status output
            status_output = gr.Textbox(
                label="Status",
                lines=4,
                interactive=False
            )
            
            # Reset chat button
            reset_btn = gr.Button("Reset Chat History", variant="secondary")
        
        with gr.Column(scale=2):
            gr.Markdown("### 💬 Chat Interface")
            
            # Chat interface
            chatbot = gr.ChatInterface(
                fn=chat_fn,
                examples=[
                    "Explain the main functionality of this repository",
                    "Show me authentication code",
                    "How does error handling work?",
                    "Find the API endpoints"
                ],
                title=str(current_repo),
                chatbot=gr.Chatbot(height=500)
            )
    
    # Event handlers
    load_btn.click(
        fn=load_repository,
        inputs=[repo_dropdown, new_repo_input],
        outputs=[status_output, load_btn]
    )
    
    reset_btn.click(
        fn=reset_chat,
        outputs=chatbot.chatbot
    )
    
    # Refresh dropdown when loading new repo
    load_btn.click(
        fn=lambda: gr.update(choices=["-- Add New Repository --"] + get_repo_list()),
        outputs=repo_dropdown
    )

# Launch app
if __name__ == "__main__":
    demo.launch()