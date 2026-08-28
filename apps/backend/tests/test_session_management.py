"""Unit tests for conversation session management (create, patch title, delete, get)."""

import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from apps.backend.server import app

client = TestClient(app)


class TestSessionManagement(unittest.TestCase):
    @patch("apps.backend.server.create_session", new_callable=AsyncMock)
    def test_create_session(self, mock_create):
        mock_create.return_value = {
            "session_id": "test-session-123",
            "user_id": "default_user",
            "title": "Custom Session",
            "created_at": "2026-08-28T10:00:00Z",
            "last_active": "2026-08-28T10:00:00Z",
        }
        res = client.post("/api/sessions", json={"title": "Custom Session"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["session"]["title"], "Custom Session")
        self.assertEqual(data["session"]["session_id"], "test-session-123")
        mock_create.assert_awaited_once_with(title="Custom Session", user_id="default_user")

    @patch("apps.backend.server.update_session", new_callable=AsyncMock)
    def test_patch_session_success(self, mock_update):
        mock_update.return_value = {
            "session_id": "test-session-123",
            "user_id": "default_user",
            "title": "Renamed Session",
            "created_at": "2026-08-28T10:00:00Z",
            "last_active": "2026-08-28T10:05:00Z",
        }
        res = client.patch("/api/sessions/test-session-123", json={"title": "Renamed Session"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["session"]["title"], "Renamed Session")
        mock_update.assert_awaited_once_with("test-session-123", title="Renamed Session")

    @patch("apps.backend.server.update_session", new_callable=AsyncMock)
    def test_patch_session_not_found(self, mock_update):
        mock_update.return_value = None
        res = client.patch("/api/sessions/non-existent-id", json={"title": "Renamed Session"})
        self.assertEqual(res.status_code, 404)
        data = res.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "Session not found")

    @patch("apps.backend.server.delete_session", new_callable=AsyncMock)
    def test_delete_session_success(self, mock_delete):
        mock_delete.return_value = True
        res = client.delete("/api/sessions/test-session-123")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "deleted")
        self.assertEqual(data["session_id"], "test-session-123")
        mock_delete.assert_awaited_once_with("test-session-123")

    @patch("apps.backend.server.delete_session", new_callable=AsyncMock)
    def test_delete_session_not_found(self, mock_delete):
        mock_delete.return_value = False
        res = client.delete("/api/sessions/non-existent-id")
        self.assertEqual(res.status_code, 404)
