from onboarding import RepoOnboarder
from ragchatbot import RAGChatbot
from dotenv import load_dotenv
from configparser import ConfigParser
import os
import json

load_dotenv()  # Load environment variables from .env
api_key = os.getenv("GOOGLE_API_KEY")
os.environ["GOOGLE_API_KEY"] = api_key

configur = ConfigParser()
configur.read('config.ini')
registry_file = configur['files'].get('registry_file')
with open(registry_file, 'r') as f:
    processed_repos = json.load(f)

repos = list(processed_repos.keys())
print("Available repos to chat: ", repos)
repo_name = input('Please select existing repository or type github link to new repo: ')

if repo_name not in repos:
    #repo_url = input('Please enter github repo link: ')
    onboarder = RepoOnboarder()
    repo_info = onboarder.onboard(repo_name)
    repo_name = repo_info['collection_name']

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