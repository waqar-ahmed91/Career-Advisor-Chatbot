from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import tempfile
import os
import fitz
from docx import Document
import ollama
# import openai
import json
import re
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

# === Config ===
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# === FastAPI Setup ===
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# === Pydantic Schema ===
class ChatRequest(BaseModel):
    query: str
    resume: str | None = None  # base64-encoded
    use_local: bool = True
    history: list[dict]

# === Resume Parsing ===
def parse_resume_from_base64(b64data):
    if not b64data:
        return ""

    decoded = base64.b64decode(b64data)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(decoded)
        tmp_path = tmp.name

    text = ""
    if tmp_path.endswith(".pdf"):
        try:
            doc = fitz.open(tmp_path)
            for page in doc:
                text += page.get_text()
        except Exception:
            text = ""
    elif tmp_path.endswith(".docx"):
        try:
            doc = Document(tmp_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        except Exception:
            text = ""

    os.remove(tmp_path)
    return text.strip()

# === LLM Wrappers ===
def query_local_llm(prompt):
    response = ollama.chat(model="granite3-dense:2b", messages=[{"role": "user", "content": prompt}], stream=True)
    # return response.get("message", {}).get("content", "(No response)")
    for chunk in response:
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content

def query_openai_stream(prompt, sponsor_tip=None):
    messages = [
        {"role": "system", "content": "You are a career advisor. Be helpful, expert, and strategic."},
        {"role": "user", "content": prompt}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            stream=True
        )

        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
        if sponsor_tip:
            yield "\n\n[[SPONSOR_BLOCK_START]]\n\n" + sponsor_tip

    except Exception as e:
        yield f"Error in OpenAI stream: {str(e)}"
    # completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages, stream=True)
    # return completion
    # return completion.choices[0].message.content.strip()
def load_sponsors(path="sponsors.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def match_sponsors(resume_text, query, sponsors, top_n=1):
    text = (resume_text + " " + query).lower()
    matched = []
    for sponsor in sponsors:
        for keyword in sponsor["keywords"]:
            if keyword.lower() in text:
                matched.append(sponsor)
                break
    return matched[:top_n]

def stream_with_sponsor(llm_stream, sponsor_tip: str):
    buffer = ""
    for token in llm_stream:
        buffer += token
        yield token

    if sponsor_tip.strip():  # Only if non-empty
        if not buffer.endswith("\n\n"):
            yield "\n\n"
        yield "\n\n[[SPONSOR_BLOCK_START]]\n\n" + sponsor_tip.strip() + "\n\n"

# Initialize Chroma client
chroma_client = chromadb.Client()

# Set up embedding function (same as used when building the KB)
chroma_client = chromadb.PersistentClient(path="chroma_db")
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Load or create collection
collection = chroma_client.get_or_create_collection(
    name="career_kb",
    embedding_function=embedding_fn
)
def retrieve_kb_context(query: str, top_k=1):
    results = collection.query(query_texts=[query], n_results=top_k)
    documents = results.get("documents", [])

    if documents and len(documents[0]) > 0:
        print("🔍 Retrieved KB Chunks:\n", "\n\n---\n\n".join(documents[0]))
        return "\n\n".join(documents[0])
    else:
        print("⚠️ No relevant KB context found.")
        return ""

@app.post("/chat")
async def chat_handler(payload: ChatRequest):
    resume_text = parse_resume_from_base64(payload.resume)
    recent_context = "\n".join([f"{m['role']}: {m['content']}" for m in payload.history])
    kb_context = retrieve_kb_context(payload.query)

    prompt_instruction = """
    You are a career advisor chatbot.
    Your goal is to:
    - Answer user questions with career guidance
    - Use relevant information from the resume or CV
    - Provide structured responses in clean Markdown format
    - Use bullet points, numbered steps, and proper headings (like #### for sections)
    - If applicable, include actionable tips, sample phrases, and clear next steps
    Respond using readable Markdown. For numbered tips, add a newline after each number (e.g., 1. ..., then a new line, then 2. ...). Use headers like ### only when necessary
    Use a newline before and after each bullet or numbered item. Format your response in Markdown for clean rendering and render sub bullets properly.
    Avoid wrapping your entire response in code blocks (e.g., ```markdown). Just use plain Markdown formatting for readability.
    Use clean markdown. Headings should be on their own line using ###, not followed immediately by other content. Avoid putting multiple headings or decorative dashes in one line.
    Avoid including any sponsor suggestions unless explicitly instructed.
    """

    full_prompt = f"""
    {prompt_instruction}

    ### Knowledge Base Insights:

    {kb_context}

    ### User Resume:

    {resume_text}

    ### Recent Conversation:

    {recent_context}

    Now respond to: {payload.query}
    """

    try:
        # Load sponsor
        sponsors = load_sponsors(path="backend/sponsors.json")
        matched = match_sponsors(resume_text, payload.query, sponsors)
        sponsor_tip = ""

        if matched:
            sponsor = matched[0]
            sponsor_tip = (
                f"💡 <strong>Sponsored Tip:</strong> Based on your background, check out "
                f"<a href='{sponsor['url']}' target='_blank' style='color:#0066cc; text-decoration:none;'>"
                f"{sponsor['title']}</a> to take your skills to the next level."
            )


        if payload.use_local:
            llm_stream = query_local_llm(full_prompt)
            return StreamingResponse(stream_with_sponsor(llm_stream, sponsor_tip), media_type="text/plain")

        else:
            return StreamingResponse(query_openai_stream(full_prompt, sponsor_tip), media_type="text/plain")
            # reply = query_openai(full_prompt)
            # return reply

            # Strip previous sponsor-like tips and marker
            # reply = re.sub(
            #     r"(?s)(-+\s*)?💡\s*\*\*Sponsored Tip:\*\*.*?(?=\n\n|\Z|\[\[SPONSOR_BLOCK_START\]\])",
            #     "",
            #     reply,
            #     flags=re.IGNORECASE
            # )
            # reply = re.sub(r"\[\[SPONSOR_BLOCK_START\]\]", "", reply).strip()

            # # Append sponsor safely
            # if sponsor_tip:
            #     reply += "\n\n[[SPONSOR_BLOCK_START]]\n\n" + sponsor_tip

            # return {"response": reply}

    except Exception as e:
        return {"response": f" Error processing request: {str(e)}"}
