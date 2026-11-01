"""Streamed-utterance buffer with speculative transcription during pauses (Spec 002)."""

import asyncio
from typing import Optional
import numpy as np
from apps.backend.services.stt import SAMPLE_RATE, pcm16_to_float32, transcribe_pcm


class UtteranceBuffer:
    """
    Accumulates PCM frames of one utterance.

    The browser VAD (the same one that decides end of turn) tells the backend when the
    speaker paused (`pause`) and when speech resumed (`resume`). On `pause` the buffer is
    transcribed speculatively in a worker thread, so the transcript is usually ready when
    the end-of-turn timeout fires. `resume` marks that result stale. The backend never
    guesses silence from signal level.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self, sample_rate: int = SAMPLE_RATE) -> None:
        self._sample_rate = sample_rate
        self._chunks: list[np.ndarray] = []
        self._spec_task: Optional[asyncio.Task] = None
        self._spec_valid = False

    def append(self, pcm: bytes) -> None:
        frame = pcm16_to_float32(pcm, self._sample_rate)
        if len(frame) > 0:
            self._chunks.append(frame)

    def _audio(self) -> np.ndarray:
        return np.concatenate(self._chunks) if self._chunks else np.zeros(0, dtype=np.float32)

    def pause(self) -> None:
        """Speaker paused: speculatively transcribe everything received so far."""
        if self._spec_valid or not self._chunks:
            return
        if self._spec_task is not None:
            self._spec_task.cancel()  # Stale earlier snapshot; its result is no longer wanted
        self._spec_valid = True
        self._spec_task = asyncio.create_task(asyncio.to_thread(transcribe_pcm, self._audio()))

    def resume(self) -> None:
        """Speech resumed after a pause: the speculative result no longer covers the utterance."""
        self._spec_valid = False

    async def finish(self) -> str:
        """Return the transcript of the buffered utterance and clear the buffer."""
        task, valid = self._spec_task, self._spec_valid
        audio = self._audio()
        self._spec_task = None
        try:
            if task is not None and valid:
                return await task
            if task is not None:
                task.cancel()
            if len(audio) == 0:
                return ""
            return await asyncio.to_thread(transcribe_pcm, audio)
        finally:
            self.reset(self._sample_rate)

    def cancel(self) -> None:
        if self._spec_task is not None:
            self._spec_task.cancel()
        self.reset(self._sample_rate)
