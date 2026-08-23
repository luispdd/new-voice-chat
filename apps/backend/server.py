"""FastAPI Server exposing REST endpoints and WebSocket streaming for Voice Chat."""

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
    add_message,
    get_messages,
    delete_session,
)
from apps.backend.services.stt import transcribe_audio, get_stt_model
from apps.backend.services.tts import text_to_wav_bytes, get_voice_model, split_into_sentences
from apps.backend.services.llm import stream_chat_completion, generate_chat_completion
from apps.backend.services.rag import ingest_document, search_relevant_chunks


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


class ChatRequest(BaseModel):
    session_id: str
    text: str
    stream: Optional[bool] = False
    with_rag: Optional[bool] = False


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
    """Synthesize text into WAV audio."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    wav_bytes = text_to_wav_bytes(text)
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
    history = await get_messages(req.session_id, limit=20)

    # Optional RAG context retrieval
    system_prompt = None
    if req.with_rag:
        relevant_chunks = await search_relevant_chunks(req.text)
        if relevant_chunks:
            context_str = "\n\n".join([f"[{c['title']}]: {c['text']}" for c in relevant_chunks])
            system_prompt = f"Use the following knowledge context to answer:\n{context_str}"

    if req.stream:
        async def event_generator():
            full_response = ""
            async for token in stream_chat_completion(history, system_prompt=system_prompt or "You are a friendly voice AI companion."):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
            # Save assistant response at the end
            await add_message(session_id=req.session_id, role="assistant", text=full_response)
            yield f"data: {json.dumps({'done': True, 'full_text': full_response})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Non-streamed response
    assistant_text = await generate_chat_completion(history, system_prompt=system_prompt or "You are a friendly voice AI companion.")
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


# WebSocket Streaming Endpoint

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Bi-directional streaming WebSocket:
    - Receives text or audio messages
    - Streams LLM text tokens and synthesized audio chunks back to the client
    """
    await websocket.accept()
    current_session_id = None

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

            if msg_type == "text" and user_text.strip():
                # Save user message
                await add_message(session_id=session_id, role="user", text=user_text)
                await websocket.send_json({"type": "user_message", "text": user_text, "session_id": session_id})

                # Stream LLM tokens and accumulate for sentence-level TTS
                history = await get_messages(session_id, limit=20)
                full_reply = ""
                sentence_buffer = ""

                async for token in stream_chat_completion(history):
                    full_reply += token
                    sentence_buffer += token
                    await websocket.send_json({"type": "token", "token": token})

                    # If sentence boundary reached, synthesize and send sentence
                    sentences = split_into_sentences(sentence_buffer)
                    if len(sentences) > 1:
                        complete_sentence = sentences[0]
                        sentence_buffer = " ".join(sentences[1:])
                        # Synthesize sentence audio
                        try:
                            wav_data = text_to_wav_bytes(complete_sentence)
                            if wav_data:
                                import base64
                                audio_b64 = base64.b64encode(wav_data).decode("utf-8")
                                await websocket.send_json({
                                    "type": "audio_sentence",
                                    "sentence": complete_sentence,
                                    "audio": audio_b64,
                                })
                        except Exception as e:
                            print(f"Error in TTS sentence synthesis: {e}")

                # Synthesize any remaining sentence buffer
                if sentence_buffer.strip():
                    try:
                        wav_data = text_to_wav_bytes(sentence_buffer.strip())
                        if wav_data:
                            import base64
                            audio_b64 = base64.b64encode(wav_data).decode("utf-8")
                            await websocket.send_json({
                                "type": "audio_sentence",
                                "sentence": sentence_buffer.strip(),
                                "audio": audio_b64,
                            })
                    except Exception as e:
                        print(f"Error in TTS final synthesis: {e}")

                # Save assistant message
                await add_message(session_id=session_id, role="assistant", text=full_reply)
                await websocket.send_json({"type": "done", "full_text": full_reply})

    except WebSocketDisconnect:
        print(f"WebSocket client disconnected for session {current_session_id}")
    except Exception as e:
        print(f"WebSocket exception: {e}")
