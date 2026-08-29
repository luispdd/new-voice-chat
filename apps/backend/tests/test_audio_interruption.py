"""Unit tests for WebSocket audio interruption and barge-in handling."""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from apps.backend.server import app

client = TestClient(app)


class TestAudioInterruption(unittest.TestCase):
    @patch("apps.backend.server.create_session", new_callable=AsyncMock)
    def test_websocket_interrupt_idle(self, mock_create):
        mock_create.return_value = {"session_id": "s-1"}
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"type": "interrupt", "session_id": "s-1"}))
            resp = json.loads(ws.receive_text())
            self.assertEqual(resp.get("type"), "interrupted")
            self.assertEqual(resp.get("session_id"), "s-1")

    @patch("apps.backend.server.add_message", new_callable=AsyncMock)
    @patch("apps.backend.server.get_messages", new_callable=AsyncMock)
    @patch("apps.backend.server.stream_chat_completion")
    def test_websocket_stream_and_interrupt(self, mock_stream, mock_get_msgs, mock_add_msg):
        mock_get_msgs.return_value = []
        mock_add_msg.return_value = {"session_id": "s-1"}

        async def slow_stream(*args, **kwargs):
            yield "Hello "
            await asyncio.sleep(0.5)
            yield "world!"

        mock_stream.return_value = slow_stream()

        with client.websocket_connect("/ws/chat") as ws:
            # Send text query
            ws.send_text(json.dumps({"type": "text", "session_id": "s-1", "text": "Hi"}))
            user_msg = json.loads(ws.receive_text())
            self.assertEqual(user_msg.get("type"), "user_message")

            token1 = json.loads(ws.receive_text())
            self.assertEqual(token1.get("type"), "token")
            self.assertEqual(token1.get("token"), "Hello ")

            # User interrupts during generation
            ws.send_text(json.dumps({"type": "interrupt", "session_id": "s-1"}))
            interrupt_msg = json.loads(ws.receive_text())
            self.assertEqual(interrupt_msg.get("type"), "interrupted")
            self.assertEqual(interrupt_msg.get("session_id"), "s-1")
