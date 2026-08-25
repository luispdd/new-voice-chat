import { Component, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';

import { ApiService, Message, Session } from '../core/api.service';
import { AudioRecordService } from '../core/audio-record.service';
import { AudioPlaybackService } from '../core/audio-playback.service';

import { VisualizerComponent } from './visualizer.component';
import { ChatHistoryComponent } from './chat-history.component';
import { VoiceInputComponent } from './voice-input.component';

@Component({
  selector: 'app-chat-container',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    VisualizerComponent,
    ChatHistoryComponent,
    VoiceInputComponent,
  ],
  template: `
    <div class="chat-app-layout">
      <!-- Sidebar / Session Drawer -->
      <aside class="sessions-sidebar" [ngClass]="{ open: isSidebarOpen() }">
        <div class="sidebar-header">
          <h2><i class="pi pi-bolt"></i> Voice Companion</h2>
          <button class="icon-btn" (click)="createNewSession()" title="New Chat">
            <i class="pi pi-plus"></i>
          </button>
        </div>

        <div class="sessions-list">
          <div
            *ngFor="let s of sessions()"
            class="session-item"
            [ngClass]="{ active: s.session_id === currentSessionId() }"
            (click)="selectSession(s.session_id)"
          >
            <i class="pi pi-comment"></i>
            <span class="session-title">{{ s.title }}</span>
            <button class="delete-btn" (click)="deleteSession(s.session_id, $event)" title="Delete">
              <i class="pi pi-trash"></i>
            </button>
          </div>
        </div>

        <div class="sidebar-footer">
          <div class="health-badge" *ngIf="healthInfo()">
            <span class="status-dot"></span>
            <span>{{ healthInfo()?.engine | uppercase }} ({{ healthInfo()?.model }})</span>
          </div>
        </div>
      </aside>

      <!-- Main Chat Area -->
      <main class="chat-main">
        <!-- Top Toolbar -->
        <header class="chat-header glass-panel">
          <div class="header-left">
            <button class="menu-btn" (click)="isSidebarOpen.set(!isSidebarOpen())">
              <i class="pi pi-bars"></i>
            </button>
            <div class="session-info">
              <h1>{{ currentSessionTitle() }}</h1>
              <span class="sub-status">{{ isConnected() ? 'Connected' : 'Connecting...' }}</span>
            </div>
          </div>

          <div class="header-right">
            <app-visualizer
              [isActive]="isRecording()"
              [isSpeaking]="isSpeaking()"
              [level]="audioLevel()"
            ></app-visualizer>
          </div>
        </header>

        <!-- Message Stream -->
        <section class="messages-viewport glass-panel">
          <app-chat-history
            [messages]="messages()"
            [isStreaming]="isStreaming()"
            [streamingText]="streamingText()"
            (onPlayAudio)="playMessageSpeech($event)"
          ></app-chat-history>
        </section>

        <!-- Input Bar -->
        <footer class="chat-input-bar glass-panel">
          <app-voice-input
            [isRecording]="isRecording()"
            [isProcessing]="isProcessingVoice()"
            [disabled]="isSpeaking() || isStreaming()"
            (onToggleMic)="toggleRecording()"
          ></app-voice-input>

          <div class="input-wrapper">
            <input
              type="text"
              [ngModel]="inputText()"
              (ngModelChange)="inputText.set($event)"
              placeholder="Ask anything or speak into your microphone..."
              (keydown.enter)="sendText()"
              [disabled]="isStreaming() || isProcessingVoice()"
            />
            <button
              class="send-btn"
              [disabled]="!inputText().trim() || isStreaming() || isProcessingVoice()"
              (click)="sendText()"
            >
              <i class="pi pi-send"></i>
            </button>
          </div>

          <button
            *ngIf="isSpeaking()"
            class="stop-audio-btn"
            (click)="stopSpeechPlayback()"
            title="Stop audio playback"
          >
            <i class="pi pi-volume-off"></i> Stop
          </button>
        </footer>
      </main>
    </div>
  `,
  styles: [`
    .chat-app-layout {
      display: flex;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
      background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #090d16 70%);
    }

    .sessions-sidebar {
      width: 280px;
      background: rgba(15, 23, 42, 0.85);
      border-right: 1px solid var(--border-glass);
      display: flex;
      flex-direction: column;
      backdrop-filter: blur(20px);
      transition: transform 0.3s ease;
      z-index: 10;

      .sidebar-header {
        padding: 1.25rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--border-glass);

        h2 {
          font-size: 1.1rem;
          font-weight: 700;
          color: var(--accent-cyan);
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
      }

      .sessions-list {
        flex: 1;
        overflow-y: auto;
        padding: 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
      }

      .session-item {
        padding: 0.75rem 1rem;
        border-radius: 10px;
        color: var(--text-secondary);
        display: flex;
        align-items: center;
        gap: 0.75rem;
        cursor: pointer;
        transition: all 0.2s ease;

        &:hover {
          background: rgba(255, 255, 255, 0.05);
          color: var(--text-primary);
        }

        &.active {
          background: rgba(56, 189, 248, 0.15);
          color: var(--accent-cyan);
          font-weight: 600;
          border: 1px solid rgba(56, 189, 248, 0.3);
        }

        .session-title {
          flex: 1;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          font-size: 0.9rem;
        }

        .delete-btn {
          background: transparent;
          border: none;
          color: var(--text-muted);
          opacity: 0;
          cursor: pointer;
          transition: opacity 0.2s;

          &:hover { color: #f43f5e; }
        }

        &:hover .delete-btn { opacity: 1; }
      }

      .sidebar-footer {
        padding: 1rem;
        border-top: 1px solid var(--border-glass);

        .health-badge {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.75rem;
          color: var(--text-muted);

          .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
          }
        }
      }
    }

    .chat-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      height: 100vh;
      padding: 1rem 1.5rem 1.5rem;
      gap: 1rem;
      max-width: 1200px;
      margin: 0 auto;
      width: 100%;
    }

    .chat-header {
      padding: 0.75rem 1.25rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-radius: 16px;

      .header-left {
        display: flex;
        align-items: center;
        gap: 1rem;

        .menu-btn {
          background: transparent;
          border: none;
          color: var(--text-primary);
          font-size: 1.25rem;
          cursor: pointer;
          display: none;
        }

        h1 {
          font-size: 1.2rem;
          font-weight: 700;
        }

        .sub-status {
          font-size: 0.75rem;
          color: #10b981;
        }
      }
    }

    .messages-viewport {
      flex: 1;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      border-radius: 20px;
    }

    .chat-input-bar {
      padding: 0.85rem 1.25rem;
      border-radius: 20px;
      display: flex;
      align-items: center;
      gap: 1rem;

      .input-wrapper {
        flex: 1;
        display: flex;
        align-items: center;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid var(--border-glass);
        border-radius: 9999px;
        padding: 0.4rem 0.5rem 0.4rem 1.25rem;

        input {
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          color: var(--text-primary);
          font-size: 0.95rem;

          &::placeholder {
            color: var(--text-muted);
          }
        }

        .send-btn {
          width: 38px;
          height: 38px;
          border-radius: 50%;
          border: none;
          background: var(--accent-blue);
          color: #fff;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: transform 0.2s;

          &:hover:not(:disabled) {
            transform: scale(1.05);
          }

          &:disabled {
            opacity: 0.4;
            cursor: not-allowed;
          }
        }
      }

      .stop-audio-btn {
        background: rgba(244, 63, 94, 0.2);
        color: #f43f5e;
        border: 1px solid rgba(244, 63, 94, 0.4);
        padding: 0.5rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 0.4rem;
      }
    }

    .icon-btn {
      background: transparent;
      border: 1px solid var(--border-glass);
      color: var(--text-primary);
      width: 32px;
      height: 32px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
      }
    }

    @media (max-width: 768px) {
      .chat-header .header-left .menu-btn {
        display: block;
      }
      .sessions-sidebar {
        position: fixed;
        left: 0;
        top: 0;
        bottom: 0;
        transform: translateX(-100%);
        &.open { transform: translateX(0); }
      }
    }
  `],
})
export class ChatContainerComponent implements OnInit, OnDestroy {
  sessions = signal<Session[]>([]);
  currentSessionId = signal<string>('');
  currentSessionTitle = signal<string>('New Conversation');
  messages = signal<Message[]>([]);
  inputText = signal<string>('');

  isSidebarOpen = signal<boolean>(false);
  isConnected = signal<boolean>(false);
  isStreaming = signal<boolean>(false);
  streamingText = signal<string>('');
  isRecording = signal<boolean>(false);
  isProcessingVoice = signal<boolean>(false);
  isSpeaking = signal<boolean>(false);
  isVadActive = signal<boolean>(false);
  audioLevel = signal<number>(0);
  healthInfo = signal<any>(null);

  private subs = new Subscription();

  constructor(
    private api: ApiService,
    private audioRecord: AudioRecordService,
    private audioPlayback: AudioPlaybackService,
  ) {}

  async ngOnInit() {
    try {
      const health = await this.api.getHealth();
      this.healthInfo.set(health);
      this.isConnected.set(true);
    } catch (e) {
      console.warn('Backend not yet reachable', e);
    }

    await this.loadSessions();

    // Listen to audio levels
    this.subs.add(
      this.audioRecord.audioLevel.subscribe((level) => {
        this.audioLevel.set(level);
      })
    );

    // Sync recording state
    this.subs.add(
      this.audioRecord.isRecording.subscribe((isRecording) => {
        this.isRecording.set(isRecording);
      })
    );

    // Listen to recorded voice chunks from VAD
    this.subs.add(
      this.audioRecord.onAudioChunkReady.subscribe(async (wavBlob) => {
        await this.handleAudioChunk(wavBlob);
      })
    );

    // Listen to playback state & auto-reactivate VAD upon completion
    this.subs.add(
      this.audioPlayback.isPlaying.subscribe(async (playing) => {
        this.isSpeaking.set(playing);
        if (playing && this.isRecording()) {
          this.audioRecord.stopRecording();
        } else if (!playing && !this.isStreaming() && !this.isProcessingVoice()) {
          await this.restartVadIfActive();
        }
      })
    );

    // Connect WebSocket for streaming
    this.subs.add(
      this.api.connectWebSocket().subscribe((event) => {
        this.handleWsEvent(event);
      })
    );
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.isVadActive.set(false);
    this.audioRecord.stopRecording();
    this.audioPlayback.stopPlayback();
  }

  async loadSessions() {
    const sessions = await this.api.getSessions();
    this.sessions.set(sessions);
    if (sessions.length > 0) {
      this.selectSession(sessions[0].session_id);
    } else {
      await this.createNewSession();
    }
  }

  async createNewSession() {
    const session = await this.api.createSession();
    this.sessions.update((s) => [session, ...s]);
    this.selectSession(session.session_id);
  }

  async selectSession(sessionId: string) {
    this.currentSessionId.set(sessionId);
    const current = this.sessions().find((s) => s.session_id === sessionId);
    if (current) {
      this.currentSessionTitle.set(current.title);
    }
    const msgs = await this.api.getMessages(sessionId);
    this.messages.set(msgs);
    this.isSidebarOpen.set(false);
  }

  async deleteSession(sessionId: string, event: Event) {
    event.stopPropagation();
    await this.api.deleteSession(sessionId);
    this.sessions.update((s) => s.filter((item) => item.session_id !== sessionId));
    if (this.currentSessionId() === sessionId) {
      if (this.sessions().length > 0) {
        this.selectSession(this.sessions()[0].session_id);
      } else {
        await this.createNewSession();
      }
    }
  }

  async sendText() {
    const text = this.inputText().trim();
    if (!text || this.isStreaming()) return;
    this.inputText.set('');

    // Optimistically add user message
    this.messages.update((msgs) => [
      ...msgs,
      {
        session_id: this.currentSessionId(),
        role: 'user',
        text,
        timestamp: new Date().toISOString(),
      },
    ]);

    // Send via WebSocket for streaming text & audio synthesis
    this.isStreaming.set(true);
    this.streamingText.set('');
    this.api.sendWsMessage({
      type: 'text',
      session_id: this.currentSessionId(),
      text,
    });
  }

  async toggleRecording() {
    if (this.isVadActive() || this.isRecording()) {
      this.isVadActive.set(false);
      this.audioRecord.stopRecording();
    } else {
      if (this.isSpeaking() || this.isProcessingVoice() || this.isStreaming()) {
        return;
      }
      this.isVadActive.set(true);
      try {
        await this.audioRecord.startRecording();
      } catch (err) {
        this.isVadActive.set(false);
        alert('Could not access microphone. Please check browser permissions and HTTPS connection.');
      }
    }
  }

  private async handleAudioChunk(blob: Blob) {
    this.isProcessingVoice.set(true);
    let shouldRestartVad = false;

    try {
      const transcribedText = await this.api.transcribeAudio(blob);
      if (transcribedText && transcribedText.trim()) {
        this.inputText.set(transcribedText);
        await this.sendText();
      } else {
        // Empty audio transcription detected
        this.messages.update((msgs) => [
          ...msgs,
          {
            session_id: this.currentSessionId(),
            role: 'assistant',
            text: 'No speech detected. Please speak into the microphone.',
            is_error: true,
            timestamp: new Date().toISOString(),
          },
        ]);
        shouldRestartVad = true;
      }
    } catch (e) {
      console.error('STT error:', e);
      this.messages.update((msgs) => [
        ...msgs,
        {
          session_id: this.currentSessionId(),
          role: 'assistant',
          text: 'Failed to transcribe audio. Please try again.',
          is_error: true,
          timestamp: new Date().toISOString(),
        },
      ]);
      shouldRestartVad = true;
    } finally {
      this.isProcessingVoice.set(false);
      if (shouldRestartVad) {
        await this.restartVadIfActive();
      }
    }
  }

  private async handleWsEvent(event: any) {
    if (event.type === 'token') {
      if (this.isRecording()) {
        this.audioRecord.stopRecording();
      }
      this.streamingText.update((t) => t + event.token);
    } else if (event.type === 'audio_sentence') {
      if (this.isRecording()) {
        this.audioRecord.stopRecording();
      }
      if (event.audio) {
        this.audioPlayback.enqueueBase64Wav(event.audio);
      }
    } else if (event.type === 'done') {
      const isError = !event.full_text || event.full_text.trim().startsWith('[Error') || event.full_text.trim() === '';
      this.messages.update((msgs) => [
        ...msgs,
        {
          session_id: this.currentSessionId(),
          role: 'assistant',
          text: event.full_text || 'Error: Empty response received from server.',
          is_error: isError,
          timestamp: new Date().toISOString(),
        },
      ]);
      this.isStreaming.set(false);
      this.streamingText.set('');

      if (!this.isSpeaking()) {
        await this.restartVadIfActive();
      }
    } else if (event.type === 'error') {
      this.messages.update((msgs) => [
        ...msgs,
        {
          session_id: this.currentSessionId(),
          role: 'assistant',
          text: event.message || 'Error communicating with assistant.',
          is_error: true,
          timestamp: new Date().toISOString(),
        },
      ]);
      this.isStreaming.set(false);
      this.streamingText.set('');
      await this.restartVadIfActive();
    }
  }

  private async restartVadIfActive() {
    if (this.isVadActive() && !this.isRecording() && !this.isSpeaking() && !this.isStreaming() && !this.isProcessingVoice()) {
      try {
        await new Promise((r) => setTimeout(r, 100));
        if (this.isVadActive() && !this.isRecording() && !this.isSpeaking() && !this.isStreaming() && !this.isProcessingVoice()) {
          await this.audioRecord.startRecording();
        }
      } catch (e) {
        console.warn('Could not auto-reactivate VAD:', e);
      }
    }
  }

  async playMessageSpeech(text: string) {
    try {
      const wavBlob = await this.api.synthesizeSpeech(text);
      await this.audioPlayback.enqueueWavBlob(wavBlob);
    } catch (e) {
      console.error('Speech synthesis error:', e);
    }
  }

  stopSpeechPlayback() {
    this.audioPlayback.stopPlayback();
  }
}
