from fastapi import FastAPI, Request
from pydantic import BaseModel
from openai import OpenAI
import chromadb

client = OpenAI(api_key="OPENAI_API_KEY")
chroma = chromadb.Client()
collection = chroma.get_or_create_collection("site_data")

# Test Data
collection.add(
    documents=[
        "Camden was incorporated in 1828. It has a rich industrial history.",
        "Walt Whitman lived in Camden. His house is now a museum.",
        "The RCA Victor Company was a major employer in Camden for decades."
    ],
    metadatas=[
        {"url": "https://camdenhistory.com/"},
        {"url": "https://camdenhistory.com/people/walt-whitman"},
        {"url": "https://camdenhistory.com/tag/RCA-Victor"}
    ],
    ids=["1", "2", "3"]
)

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/ask")
def ask_question(request: QueryRequest):
    query = request.query

    # Get embedding
    query_embedding = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    ).data[0].embedding

    # Semantic search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    context = "\n\n".join(
        f"Source: {m['url']}\nText: {d}"
        for m, d in zip(results['metadatas'][0], results['documents'][0])
    )

    prompt = f"""You are a helpful AI assistant. Use the following content to answer the question at approximately an 8th grade reading level. Include source links.

Context:
{context}

Question: {query}
"""

    chat_response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    answer = chat_response.choices[0].message.content
    return {"answer": answer}
