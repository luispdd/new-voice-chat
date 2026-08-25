# ADR 005: Sentence-Boundary Streaming TTS

## Context
Waiting for a complete LLM response before initiating Text-to-Speech synthesis results in high latency (poor Time-to-First-Audio / TTFA). Synthesizing token-by-token results in unnatural, robotic, and clipped audio.

## Decision
- Stream LLM tokens in real time into an internal buffer.
- Detect natural sentence termination punctuation (`[.!?\n]`).
- Synthesize each complete sentence into 22050Hz 16-bit PCM WAV audio using Piper TTS and transmit immediately to the client over WebSocket.
- The frontend `AudioPlaybackService` queues incoming sentence chunks in an `AudioContext` buffer queue to ensure continuous, gapless speech.

## Consequences
- Reduces Time-to-First-Audio (TTFA) to the duration of the first generated sentence (<1 second).
- Maintains natural prosody and intonation by synthesizing full grammatical sentences.
