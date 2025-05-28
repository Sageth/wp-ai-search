# See uvicorn.service

from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import pdfplumber

# --- Config ---
CHROMA_PATH = "/path/to/chroma-db/"     # Must match what is in index.py
COLLECTION_NAME = "dvrbs_site"          # Must match what is in index.py
EMBED_MODEL = "text-embedding-3-small"  # Must match what is in index.py

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.environ["OPENAI_API_KEY"],
    model_name=EMBED_MODEL
)

# --- Clients ---
print("Chroma Path: ", CHROMA_PATH)

openai_client = OpenAI()  # Uses env var: OPENAI_API_KEY
chroma = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=openai_ef
)

print("Chroma DB Path: ", CHROMA_PATH)
print("Collections: ", chroma.list_collections())

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.post("/ask")
def ask_question(request: QueryRequest):
    query = request.query

    # Embed user query
    try:
        query_embedding = openai_client.embeddings.create(
            input=query,
            model=EMBED_MODEL
        ).data[0].embedding
    except Exception as e:
        return {"error": f"Embedding error: {e}"}

    # Search collection
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5
        )
    except Exception as e:
        return {"error": f"Chroma query error: {e}"}

    # Build context from documents and extract source titles
    context_blocks = []
    sources = {}

    for metadata, document in zip(results['metadatas'][0], results['documents'][0]):
        url = metadata.get("source", "")
        context_blocks.append(f"Text: {document}")
        sources[url] = None

    context = "\n\n".join(context_blocks)

    for url in sources:
        try:
            if url.endswith(".pdf"):
                # Extract title from PDF if accessible locally
                parsed = urlparse(url)
                local_path = os.path.join("/path/to/files", parsed.path.lstrip("/"))
                if os.path.isfile(local_path):
                    with pdfplumber.open(local_path) as pdf:
                        title = pdf.metadata.get("Title", os.path.basename(local_path))
                else:
                    title = os.path.basename(url)
            else:
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    title = soup.title.string.strip() if soup.title else url
                else:
                    title = urlparse(url).netloc
        except:
            title = urlparse(url).netloc
        sources[url] = title

    sources_markdown = "\n".join(
        f"- [{title}]({url})" for url, title in sources.items()
    )

    prompt = f"""You are a helpful AI assistant. Use only the context provided below to answer the question. Do not use outside knowledge.

Context:
{context}

Question: {query}"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content.strip()
        answer += f"\n\n**Sources:**\n\n{sources_markdown}"
        return {"answer": answer}
    except Exception as e:
        return {"error": f"Chat response error: {e}"}

