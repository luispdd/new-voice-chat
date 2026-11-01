"""Unit tests for Parakeet STT helpers and streamed utterance buffering (Spec 002)."""

import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from fastapi.testclient import TestClient

from apps.backend.server import app
from apps.backend.services import stt
from apps.backend.services.stt_stream import UtteranceBuffer


def pcm(seconds: float, amplitude: float = 0.0, rate: int = 16000) -> bytes:
    """16-bit PCM bytes: a sine wave of the given amplitude (0 = silence)."""
    t = np.arange(int(seconds * rate)) / rate
    wave = amplitude * np.sin(2 * np.pi * 220 * t)
    return (wave * 32767).astype("<i2").tobytes()


class TestPcmHelpers(unittest.TestCase):
    def test_pcm16_to_float32_scales_samples(self):
        out = stt.pcm16_to_float32(np.array([0, 16384, -32768], dtype="<i2").tobytes())
        np.testing.assert_allclose(out, [0.0, 0.5, -1.0])

    def test_pcm16_ignores_trailing_odd_byte(self):
        self.assertEqual(len(stt.pcm16_to_float32(b"\x00\x01\x02")), 1)

    def test_pcm16_resamples_to_16k(self):
        out = stt.pcm16_to_float32(pcm(1.0, 0.3, rate=48000), sample_rate=48000)
        self.assertAlmostEqual(len(out), 16000, delta=64)

    def test_transcribe_pcm_short_audio_is_empty(self):
        self.assertEqual(stt.transcribe_pcm(np.zeros(100, dtype=np.float32)), "")

    def test_transcribe_pcm_silence_is_empty(self):
        self.assertEqual(stt.transcribe_pcm(np.zeros(16000, dtype=np.float32)), "")

    def test_transcribe_pcm_decodes_speech(self):
        speech = stt.pcm16_to_float32(pcm(1.0, 0.3))
        with patch.object(stt, "get_stt_model", return_value=MagicMock()), patch.object(
            stt, "_decode", return_value="hello world"
        ) as decode:
            self.assertEqual(stt.transcribe_pcm(speech), "hello world")
            decode.assert_called_once()

    def test_transcribe_pcm_retries_normalized_on_empty_result(self):
        speech = stt.pcm16_to_float32(pcm(1.0, 0.3))
        with patch.object(stt, "get_stt_model", return_value=MagicMock()), patch.object(
            stt, "_decode", side_effect=["", "retry text"]
        ) as decode:
            self.assertEqual(stt.transcribe_pcm(speech), "retry text")
            self.assertEqual(decode.call_count, 2)


class TestUtteranceBuffer(unittest.IsolatedAsyncioTestCase):
    async def test_pause_speculates_and_finish_reuses_result(self):
        calls = []

        def fake_transcribe(audio):
            calls.append(len(audio))
            return "spoken text"

        with patch("apps.backend.services.stt_stream.transcribe_pcm", fake_transcribe):
            buf = UtteranceBuffer()
            buf.append(pcm(1.0, 0.3))
            buf.pause()
            await asyncio.sleep(0.05)
            self.assertEqual(len(calls), 1)  # speculation ran during the pause
            buf.append(pcm(0.7))  # silence until the end-of-turn timeout
            self.assertEqual(await buf.finish(), "spoken text")
            self.assertEqual(len(calls), 1)  # no second transcription

    async def test_quiet_audio_never_triggers_speculation_without_a_pause_hint(self):
        with patch("apps.backend.services.stt_stream.transcribe_pcm", return_value="x") as t:
            buf = UtteranceBuffer()
            for _ in range(20):
                buf.append(pcm(0.1, 0.001))  # very quiet speech must not be treated as silence
            await asyncio.sleep(0.05)
            t.assert_not_called()

    async def test_resume_invalidates_speculation(self):
        calls = []

        def fake_transcribe(audio):
            calls.append(len(audio))
            return f"text-{len(calls)}"

        with patch("apps.backend.services.stt_stream.transcribe_pcm", fake_transcribe):
            buf = UtteranceBuffer()
            buf.append(pcm(1.0, 0.3))
            buf.pause()
            await asyncio.sleep(0.05)
            buf.resume()  # user keeps talking after a breath
            buf.append(pcm(1.0, 0.3))
            self.assertEqual(await buf.finish(), "text-2")
            self.assertEqual(len(calls), 2)
            self.assertGreater(calls[1], calls[0])  # final pass covers the extra speech

    async def test_second_pause_after_resume_speculates_again(self):
        calls = []

        def fake_transcribe(audio):
            calls.append(len(audio))
            return f"text-{len(calls)}"

        with patch("apps.backend.services.stt_stream.transcribe_pcm", fake_transcribe):
            buf = UtteranceBuffer()
            buf.append(pcm(1.0, 0.3))
            buf.pause()
            await asyncio.sleep(0.05)
            buf.resume()
            buf.append(pcm(1.0, 0.3))
            buf.pause()
            await asyncio.sleep(0.05)
            self.assertEqual(await buf.finish(), "text-2")
            self.assertEqual(len(calls), 2)  # second speculation was reused, no third pass

    async def test_finish_without_speculation_transcribes_full_buffer(self):
        with patch("apps.backend.services.stt_stream.transcribe_pcm", return_value="quick") as t:
            buf = UtteranceBuffer()
            buf.append(pcm(0.5, 0.3))
            self.assertEqual(await buf.finish(), "quick")
            t.assert_called_once()

    async def test_finish_on_empty_buffer_returns_empty(self):
        buf = UtteranceBuffer()
        self.assertEqual(await buf.finish(), "")


class TestWebSocketAudio(unittest.TestCase):
    def test_audio_stream_returns_transcript_without_creating_session(self):
        client = TestClient(app)
        with patch("apps.backend.services.stt_stream.transcribe_pcm", return_value="hello there"), patch(
            "apps.backend.server.create_session"
        ) as create_session:
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_text(json.dumps({"type": "audio_start", "sample_rate": 16000}))
                ws.send_bytes(pcm(0.5, 0.3))
                ws.send_text(json.dumps({"type": "audio_pause"}))
                ws.send_text(json.dumps({"type": "audio_resume"}))
                ws.send_text(json.dumps({"type": "audio_end"}))
                resp = json.loads(ws.receive_text())
            self.assertEqual(resp, {"type": "transcript", "text": "hello there"})
            create_session.assert_not_called()

    def test_audio_end_without_audio_returns_empty_transcript(self):
        client = TestClient(app)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"type": "audio_start", "sample_rate": 16000}))
            ws.send_text(json.dumps({"type": "audio_end"}))
            resp = json.loads(ws.receive_text())
        self.assertEqual(resp, {"type": "transcript", "text": ""})


if __name__ == "__main__":
    unittest.main()

