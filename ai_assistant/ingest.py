import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

# Only index important folders
TARGET_FOLDERS = [
    "../app",
    "../templates",
    "../utils"
]

docs = []

for folder in TARGET_FOLDERS:
    if os.path.exists(folder):
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith((".py", ".html", ".js", ".css", ".txt")):
                    try:
                        path = os.path.join(root, file)
                        loader = TextLoader(path, encoding="utf-8")
                        docs.extend(loader.load())
                    except:
                        pass

print(f"Loaded {len(docs)} project files")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

chunks = splitter.split_documents(docs)

embeddings = OllamaEmbeddings(model="nomic-embed-text")

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

vectorstore.persist()
print("✅ Project indexed successfully!")