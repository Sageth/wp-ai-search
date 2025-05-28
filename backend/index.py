# indexing/indexer.py
"""
Runs the indexing requests of the files ending in .htm and .html, as well as PDFs and crawling the BASE_DOMAIN.
"""
# indexing/indexer.py

import os
import io
import json
import time
import psutil
import hashlib
import requests
import chromadb
import tiktoken
import pdfplumber
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from openai import OpenAI
from urllib.parse import quote, urljoin
from chromadb.utils import embedding_functions
from tqdm import tqdm
import argparse

# --- Config ---
LOCAL_MIRROR_PATH = "/path/to/files_to_scan"
BASE_DOMAIN = "https://example.com"
SITEMAP_URL = "https://example.com/sitemap.xml"
COLLECTION_NAME = "dvrbs_site"          # Must match what is in main.py
CHROMA_PATH = "/path/to/chroma-db/"     # Must match what is in main.py
EMBED_MODEL = "text-embedding-3-small"  # Must match what is in main.py
MAX_CHUNK_TOKENS = 2000                 # Must match what is in main.py
AUDIT_TERMS = ["Vincent Tydeman", "Walt Whitman", "RCA Victor"]
STATE_FILE = "index_progress.json"

# --- Clients ---
openai_client = OpenAI()
encoding = tiktoken.encoding_for_model(EMBED_MODEL)
embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.environ["OPENAI_API_KEY"],
    model_name=EMBED_MODEL
)
chroma = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_fn
)

# --- Logs ---
skipped_files = []
error_chunks = []
audit_misses = []
visited_urls = set()
existing_hashes = set()

# --- State ---
progress = {
    "completed_local": [],
    "completed_urls": []
}
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        try:
            progress = json.load(f)
        except: pass

# --- Helpers ---
def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(progress, f)
    with open("skipped_files.json", "w") as f:
        json.dump(skipped_files, f, indent=2)
    with open("embedding_errors.json", "w") as f:
        json.dump(error_chunks, f, indent=2)

def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def list_local_files():
    for root, _, files in os.walk(LOCAL_MIRROR_PATH):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext in (".html", ".htm", ".pdf"):
                full_path = os.path.join(root, name)
                yield os.path.relpath(full_path, LOCAL_MIRROR_PATH)

def fetch_local_file(rel_path):
    try:
        full_path = os.path.join(LOCAL_MIRROR_PATH, rel_path)
        with open(full_path, "rb") as f:
            return f.read()
    except Exception as e:
        skipped_files.append({"key": rel_path, "reason": "read error", "error": str(e)})
        return None

def fetch_url_html(url):
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        skipped_files.append({"key": url, "reason": "fetch error", "error": str(e)})
    return None

def extract_text_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "meta", "head"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())

def extract_text_from_pdf(data):
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return ""

def chunk_text(text, max_tokens=MAX_CHUNK_TOKENS):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_tokens = 0
    current_chunk = []
    for para in paragraphs:
        tokens = encoding.encode(para)
        if len(tokens) > max_tokens:
            continue
        if current_tokens + len(tokens) > max_tokens:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = [para]
            current_tokens = len(tokens)
        else:
            current_chunk.append(para)
            current_tokens += len(tokens)
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def embed_and_store_chunk(doc_id, chunk, source_url):
    h = sha256(chunk)
    if h in existing_hashes:
        return
    try:
        time.sleep(0.5)
        embedding = openai_client.embeddings.create(input=chunk, model=EMBED_MODEL).data[0].embedding
        collection.add(
            documents=[chunk],
            metadatas=[{"source": source_url}],
            ids=[doc_id]
        )
        existing_hashes.add(h)
    except Exception as e:
        error_chunks.append({"key": doc_id, "error": str(e)})

def crawl_from_sitemap(sitemap_url):
    try:
        res = requests.get(sitemap_url, timeout=10)
        res.raise_for_status()
        root = ET.fromstring(res.text)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        return [loc.text for loc in root.findall(".//ns:loc", ns)]
    except Exception as e:
        skipped_files.append({"key": sitemap_url, "reason": "sitemap parse error", "error": str(e)})
        return []

# --- Main index loop ---
def index_all(max_items):
    local_keys = list(list_local_files())
    for idx, key in enumerate(tqdm(local_keys)):
        if key in progress["completed_local"]:
            continue
        ext = os.path.splitext(key)[1].lower()
        data = fetch_local_file(key)
        if not data:
            continue
        if ext in (".html", ".htm"):
            text = extract_text_from_html(data.decode("utf-8", errors="ignore"))
        elif ext == ".pdf":
            text = extract_text_from_pdf(data)
        else:
            continue
        if not text:
            skipped_files.append({"key": key, "reason": "no text"})
            continue
        chunks = chunk_text(text)
        public_url = f"https://www.example.com/{quote(key)}"
        for i, chunk in enumerate(chunks):
            embed_and_store_chunk(f"{key}#{i}", chunk, public_url)
        progress["completed_local"].append(key)
        if max_items and len(progress["completed_local"]) >= max_items:
            break
        if idx % 50 == 0:
            save_state()

    urls = crawl_from_sitemap(SITEMAP_URL)
    for idx, url in enumerate(tqdm(urls)):
        if url in progress["completed_urls"]:
            continue
        html = fetch_url_html(url)
        if not html:
            continue
        text = extract_text_from_html(html)
        if not text:
            skipped_files.append({"key": url, "reason": "no text"})
            continue
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            embed_and_store_chunk(f"{url}#{i}", chunk, url)
        progress["completed_urls"].append(url)
        if max_items and len(progress["completed_urls"]) >= max_items:
            break
        if idx % 50 == 0:
            save_state()

# --- Run ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=None, help="Max number of files/URLs to index")
    args = parser.parse_args()

    print("🔍 Indexing all documents...")
    try:
        index_all(args.max)
    finally:
        print("🔁 Saving final state...")
        save_state()
        print("✅ Done.")
        print(f"⚠️ Skipped: {len(skipped_files)} files")
        print(f"❌ Errors: {len(error_chunks)} chunks")
