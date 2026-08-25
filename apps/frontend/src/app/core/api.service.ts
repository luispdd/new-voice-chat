import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

export interface Session {
  session_id: string;
  user_id: string;
  title: string;
  created_at: string;
  last_active: string;
}

export interface Message {
  message_id?: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  text: string;
  timestamp?: string;
  audio_url?: string;
  is_error?: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  // Use current host origin or default port 8000
  private baseUrl = window.location.protocol + '//' + window.location.hostname + ':8000';
  private wsUrl = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.hostname + ':8000/ws/chat';
  private ws: WebSocket | null = null;
  private wsMessages$ = new Subject<any>();

  constructor() {}

  async getHealth(): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/health`);
    return res.json();
  }

  async getSessions(): Promise<Session[]> {
    const res = await fetch(`${this.baseUrl}/api/sessions`);
    const data = await res.json();
    return data.sessions || [];
  }

  async createSession(title: string = 'New Conversation'): Promise<Session> {
    const res = await fetch(`${this.baseUrl}/api/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    const data = await res.json();
    return data.session;
  }

  async getMessages(sessionId: string): Promise<Message[]> {
    const res = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/messages`);
    const data = await res.json();
    return data.messages || [];
  }

  async deleteSession(sessionId: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    return res.json();
  }

  async sendChatMessage(sessionId: string, text: string, withRag: boolean = false): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        text,
        stream: false,
        with_rag: withRag,
      }),
    });
    return res.json();
  }

  async transcribeAudio(audioBlob: Blob): Promise<string> {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'mic.wav');
    const res = await fetch(`${this.baseUrl}/api/transcribe`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    return data.text || '';
  }

  async synthesizeSpeech(text: string): Promise<Blob> {
    const formData = new URLSearchParams();
    formData.set('text', text);
    const res = await fetch(`${this.baseUrl}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });
    return res.blob();
  }

  // WebSocket Connection
  connectWebSocket(): Observable<any> {
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.wsMessages$.next(data);
        } catch (e) {
          console.error('Error parsing WS message', e);
        }
      };

      this.ws.onerror = (err) => console.error('WebSocket error:', err);
      this.ws.onclose = () => console.log('WebSocket closed');
    }
    return this.wsMessages$.asObservable();
  }

  sendWsMessage(payload: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }
}
