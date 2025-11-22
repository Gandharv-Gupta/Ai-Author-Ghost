from fastapi.responses import StreamingResponse
from groq import stream_llm_response
# Streaming chat endpoint with debug
from fastapi.responses import StreamingResponse
from groq import stream_llm_response

from fastapi.responses import RedirectResponse

from process_pdf import ingest_pdf
from groq import generate_llm_response
from prompt_handler import set_llm_prompt
from utils import query_chroma
import json

import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import shutil


from typing import List, Optional
from fastapi import Body
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
	question: str
	k: Optional[int] = 3
	history: Optional[List[dict]] = None
     

# Streaming chat endpoint
@app.post("/chat_stream/")
async def chat_stream(request: ChatRequest):
    """
    Streams the LLM response word by word for a multi-turn chat. Includes debug prints.
    """
    try:
        chat_history = request.history or []
        results = query_chroma(request.question, k=request.k)
        docs = results["documents"][0]
        sources = "\n---\n".join(docs)
        conversation = ""
        for turn in chat_history:
            if turn.get("role") == "user":
                conversation += f"User: {turn.get('content')}\n"
            elif turn.get("role") == "author":
                conversation += f"Author: {turn.get('content')}\n"
        conversation += f"User: {request.question}\n"

        prompt = set_llm_prompt(conversation, request.question, sources)
        print("\n--- LLM PROMPT ---\n", prompt, "\n--- END PROMPT ---\n")

        def word_stream():
            buffer = ""
            for chunk in stream_llm_response(prompt):
                print("[DEBUG] LLM chunk:", repr(chunk))
                buffer += chunk
                while " " in buffer:
                    word, buffer = buffer.split(" ", 1)
                    yield word + " "
            if buffer:
                yield buffer

        return StreamingResponse(word_stream(), media_type="text/plain")
    except Exception as e:
        print("[ERROR in /chat_stream/]:", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

# Endpoint to upload and ingest a PDF
@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
	temp_path = f"./uploaded_{file.filename}"
	with open(temp_path, "wb") as buffer:
		shutil.copyfileobj(file.file, buffer)
	try:
		ingest_pdf(temp_path)
		os.remove(temp_path)
		return {"status": "success", "message": f"Ingested {file.filename}"}
	except Exception as e:
		if os.path.exists(temp_path):
			os.remove(temp_path)
		return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# Endpoint to ask a question (RAG)

# Multi-turn chat endpoint

# Pydantic model for chat request




@app.post("/chat/")
async def ask_question(request: ChatRequest):
    """
    Multi-turn chat endpoint. Accepts a question and optional chat history (as a list of dicts with 'role' and 'content').
    Returns the answer and updated history. Adds debug prints and always returns a 'response' field.
    """
    try:
        chat_history = request.history or []
        # Retrieve top-k relevant chunks
        results = query_chroma(request.question, k=request.k)
        docs = results["documents"][0]
        sources = "\n---\n".join(docs)
        # Compose prompt with history
        conversation = ""
        for turn in chat_history:
            if turn.get("role") == "user":
                conversation += f"User: {turn.get('content')}\n"
            elif turn.get("role") == "author":
                conversation += f"Author: {turn.get('content')}\n"
        conversation += f"User: {request.question}\n"

        prompt = set_llm_prompt(conversation, request.question, sources)
        print("\n--- LLM PROMPT (non-stream) ---\n", prompt, "\n--- END PROMPT ---\n")
        answer = None
        try:
            answer = generate_llm_response(prompt)
            print("[DEBUG] LLM answer:", repr(answer))
        except Exception as llm_exc:
            print("[ERROR] LLM call failed:", llm_exc)
            answer = None

        # Update history
        chat_history.append({"role": "user", "content": request.question})
        chat_history.append({"role": "author", "content": answer if answer else "(No response)"})

        # Always return a 'response' field for frontend compatibility
        if answer and answer.strip():
            return {"response": answer, "context": docs, "history": chat_history}
        else:
            return {"response": "(No response)", "context": docs, "history": chat_history}
    except Exception as e:
        print("[ERROR in /chat/]:", e)
        return {"response": "(Error: No response from server)", "error": str(e)}


# Endpoint to list all embeddings stored in ChromaDB
@app.get("/list_embeddings/")
async def list_embeddings():
	try:
		import chromadb
		CHROMA_DIR = "./chromadb_store"
		COLLECTION_NAME = "pdf_chunks"
		client = chromadb.PersistentClient(path=CHROMA_DIR)
		collection = client.get_collection(COLLECTION_NAME)
		# Get all ids and metadatas
		results = collection.get()
		# Only return id, metadata, and optionally document (not full embedding array)
		response = []
		for i, id_ in enumerate(results["ids"]):
			entry = {
				"id": id_,
				"metadata": results["metadatas"][i],
				"document": results["documents"][i]
			}
			response.append(entry)
		return {"embeddings": response}
	except Exception as e:
		return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# Endpoint to clear all data in ChromaDB collection
@app.post("/clear_chromadb/")
async def clear_chromadb():
    try:
        import chromadb
        CHROMA_DIR = "./chromadb_store"
        COLLECTION_NAME = "pdf_chunks"
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        collection = client.get_collection(COLLECTION_NAME)
        collection.delete(where={})
        return {"status": "success", "message": "All data cleared from ChromaDB collection."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})



