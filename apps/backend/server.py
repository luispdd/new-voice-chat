"""FastAPI Server exposing REST endpoints and WebSocket streaming for Voice Chat."""

import asyncio
import base64
from contextlib import asynccontextmanager
import json
from typing import Any, Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from apps.backend.config import settings
from apps.backend.db.mongo import (
    init_db,
    close_db,
    create_session,
    get_sessions,
    get_session,
    update_session,
    add_message,
    get_messages,
    delete_session,
)
from apps.backend.services.stt import transcribe_audio, get_stt_model
from apps.backend.services.tts import text_to_wav_bytes, get_voice_model, split_into_sentences, sanitize_for_tts
from apps.backend.services.llm import stream_chat_completion, generate_chat_completion, SYSTEM_PROMPT
from apps.backend.services.rag import (
    ingest_document,
    search_relevant_chunks,
    session_has_documents,
    get_session_documents,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect DB and warmup neural models
    print("🚀 Initializing Voice Chat Backend...")
    await init_db()
    try:
        get_stt_model()
    except Exception as e:
        print(f"⚠️ Warning initializing STT model: {e}")
    try:
        get_voice_model()
    except Exception as e:
        print(f"⚠️ Warning initializing TTS model: {e}")

    yield

    # Shutdown: close DB connections
    print("🛑 Shutting down Voice Chat Backend...")
    await close_db()


app = FastAPI(
    title="Voice Chat API",
    version="0.1.0",
    description="Real-time Voice Chat Companion API with STT, TTS, LLM and MongoDB",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request & Response Models

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Conversation"
    user_id: Optional[str] = "default_user"


class UpdateSessionRequest(BaseModel):
    title: str


class ChatRequest(BaseModel):
    session_id: str
    text: str
    stream: Optional[bool] = False


class IngestDocRequest(BaseModel):
    title: str
    content: str


# REST Endpoints

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "engine": settings.engine,
        "model": settings.llm_model,
        "stt": settings.stt_model_name,
        "tts_repo": settings.tts_repo_id,
    }


# Session Management

@app.get("/api/sessions")
async def list_sessions(user_id: str = "default_user"):
    sessions = await get_sessions(user_id=user_id)
    return {"sessions": sessions}


@app.post("/api/sessions")
async def new_session(req: CreateSessionRequest):
    session = await create_session(title=req.title or "New Conversation", user_id=req.user_id or "default_user")
    return {"session": session}


@app.patch("/api/sessions/{session_id}")
async def modify_session(session_id: str, req: UpdateSessionRequest):
    updated = await update_session(session_id, title=req.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": updated}


@app.get("/api/sessions/{session_id}/messages")
async def list_messages(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await get_messages(session_id)
    return {"messages": messages}


@app.delete("/api/sessions/{session_id}")
async def remove_session(session_id: str):
    success = await delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


# Audio STT Endpoint

@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Transcribe uploaded audio file to text."""
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    text = transcribe_audio(content)
    return {"text": text}


# TTS Synthesis Endpoint

@app.post("/api/tts")
async def synthesize(text: str = Form(...)):
    """Synthesize text into WAV audio, returning empty audio for unreadable or silent input."""
    clean_text = sanitize_for_tts(text)
    if not clean_text:
        return Response(content=b"", media_type="audio/wav")

    wav_bytes = text_to_wav_bytes(clean_text)
    return Response(content=wav_bytes, media_type="audio/wav")


# Chat Completion Endpoint

@app.post("/api/chat")
async def chat(req: ChatRequest):
    session = await get_session(req.session_id)
    if not session:
        session = await create_session(title="Conversation", user_id="default_user")
        req.session_id = session["session_id"]

    # Save user message
    await add_message(session_id=req.session_id, role="user", text=req.text)

    # Fetch past message history for context
    history = await get_messages(req.session_id, limit=settings.llm_history_limit)

    # Auto-RAG: inject document context when session has attached documents
    system_prompt = SYSTEM_PROMPT
    if await session_has_documents(req.session_id):
        relevant_chunks = await search_relevant_chunks(req.text, session_id=req.session_id)
        if relevant_chunks:
            context_str = "\n\n".join([f"[{c['title']}]: {c['text']}" for c in relevant_chunks])
            system_prompt = f"{SYSTEM_PROMPT}\n\nUse the following knowledge context to answer:\n{context_str}"

    if req.stream:
        async def event_generator():
            full_response = ""
            async for token in stream_chat_completion(history, system_prompt=system_prompt):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
            # Save assistant response at the end
            await add_message(session_id=req.session_id, role="assistant", text=full_response)
            yield f"data: {json.dumps({'done': True, 'full_text': full_response})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Non-streamed response
    assistant_text = await generate_chat_completion(history, system_prompt=system_prompt)
    assistant_msg = await add_message(session_id=req.session_id, role="assistant", text=assistant_text)

    return {
        "reply": assistant_text,
        "message": assistant_msg,
    }


# RAG Ingestion Endpoint

@app.post("/api/documents")
async def add_document(req: IngestDocRequest):
    doc = await ingest_document(title=req.title, content=req.content)
    return {"status": "ingested", "document": doc}


@app.post("/api/sessions/{session_id}/documents")
async def upload_session_document(session_id: str, file: UploadFile = File(...)):
    """Attach a .txt or .md file to a chat session for RAG context."""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    filename = file.filename or "untitled.txt"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("txt", "md"):
        raise HTTPException(status_code=400, detail="Only .txt and .md files are supported")

    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")

    if not content.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    doc = await ingest_document(title=filename, content=content, session_id=session_id)
    return {
        "status": "ingested",
        "document": {
            "_id": doc["_id"],
            "title": doc["title"],
            "session_id": session_id,
            "chunk_count": len(doc.get("chunks", [])),
        },
    }


@app.get("/api/sessions/{session_id}/documents")
async def list_session_documents(session_id: str):
    """List documents attached to a chat session."""
    docs = await get_session_documents(session_id)
    return {"documents": docs}


# WebSocket Streaming Endpoint

async def _stream_chat_and_synthesize(websocket: WebSocket, session_id: str, user_text: str):
    full_reply = ""
    sentence_buffer = ""
    try:
        # Save user message
        await add_message(session_id=session_id, role="user", text=user_text)
        await websocket.send_json({"type": "user_message", "text": user_text, "session_id": session_id})

        # Stream LLM tokens and accumulate for sentence-level TTS
        history = await get_messages(session_id, limit=settings.llm_history_limit)

        # Auto-RAG: inject document context when session has attached documents
        system_prompt = SYSTEM_PROMPT
        if await session_has_documents(session_id):
            relevant_chunks = await search_relevant_chunks(user_text, session_id=session_id)
            if relevant_chunks:
                context_str = "\n\n".join([f"[{c['title']}]: {c['text']}" for c in relevant_chunks])
                system_prompt = f"{SYSTEM_PROMPT}\n\nUse the following knowledge context to answer:\n{context_str}"

        async for token in stream_chat_completion(history, system_prompt=system_prompt):
            full_reply += token
            sentence_buffer += token
            await websocket.send_json({"type": "token", "token": token})

            # If sentence boundary reached, synthesize and send sentence
            sentences = split_into_sentences(sentence_buffer)
            if len(sentences) > 1:
                complete_sentence = sentences[0]
                sentence_buffer = " ".join(sentences[1:])
                clean_sentence = sanitize_for_tts(complete_sentence)
                if clean_sentence:
                    try:
                        wav_data = text_to_wav_bytes(clean_sentence)
                        if wav_data:
                            audio_b64 = base64.b64encode(wav_data).decode("utf-8")
                            await websocket.send_json({
                                "type": "audio_sentence",
                                "sentence": clean_sentence,
                                "audio": audio_b64,
                            })
                    except Exception as e:
                        print(f"Error in TTS sentence synthesis: {e}")

        # Synthesize any remaining sentence buffer
        if sentence_buffer.strip():
            clean_sentence = sanitize_for_tts(sentence_buffer.strip())
            if clean_sentence:
                try:
                    wav_data = text_to_wav_bytes(clean_sentence)
                    if wav_data:
                        audio_b64 = base64.b64encode(wav_data).decode("utf-8")
                        await websocket.send_json({
                            "type": "audio_sentence",
                            "sentence": clean_sentence,
                            "audio": audio_b64,
                        })
                except Exception as e:
                    print(f"Error in TTS final synthesis: {e}")

        # Save assistant message
        if full_reply.strip():
            await add_message(session_id=session_id, role="assistant", text=full_reply)
            await websocket.send_json({"type": "done", "full_text": full_reply})
    except asyncio.CancelledError:
        print(f"Generation cancelled for session {session_id}")
        if full_reply.strip():
            try:
                await add_message(session_id=session_id, role="assistant", text=full_reply)
            except Exception:
                pass
        raise
    except Exception as e:
        print(f"Error during streaming generation: {e}")
        try:
            await websocket.send_json({"type": "error", "message": f"[Error: {str(e)}]"})
        except Exception:
            pass


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Bi-directional streaming WebSocket:
    - Receives text, interrupt, or audio messages
    - Streams LLM text tokens and synthesized audio chunks back to the client
    - Supports real-time cancellation / barge-in
    """
    await websocket.accept()
    current_session_id = None
    active_task: Optional[asyncio.Task] = None

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            msg_type = payload.get("type", "text")
            session_id = payload.get("session_id")
            user_text = payload.get("text", "")

            if not session_id:
                session = await create_session()
                session_id = session["session_id"]
                current_session_id = session_id
                await websocket.send_json({"type": "session_created", "session_id": session_id})
            else:
                current_session_id = session_id

            if msg_type == "interrupt":
                if active_task and not active_task.done():
                    active_task.cancel()
                    try:
                        await active_task
                    except asyncio.CancelledError:
                        pass
                    active_task = None
                await websocket.send_json({"type": "interrupted", "session_id": session_id})

            elif msg_type == "text" and user_text.strip():
                if active_task and not active_task.done():
                    active_task.cancel()
                    try:
                        await active_task
                    except asyncio.CancelledError:
                        pass
                    active_task = None

                active_task = asyncio.create_task(
                    _stream_chat_and_synthesize(websocket, session_id, user_text)
                )

    except WebSocketDisconnect:
        print(f"WebSocket client disconnected for session {current_session_id}")
    except Exception as e:
        print(f"WebSocket exception: {e}")
    finally:
        if active_task and not active_task.done():
            active_task.cancel()
            try:
                await active_task
            except (asyncio.CancelledError, Exception):
                pass
