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
  templateUrl: './chat-container.component.html',
  styleUrl: './chat-container.component.scss',
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
