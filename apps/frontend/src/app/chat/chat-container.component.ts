import { Component, OnInit, OnDestroy, signal, computed, effect, inject, viewChild, untracked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ApiService, Message, Session, SessionDocument } from '../core/api.service';
import { AudioRecordService } from '../core/audio-record.service';
import { AudioPlaybackService } from '../core/audio-playback.service';

import { ChatHistoryComponent } from './chat-history.component';
import { VoiceInputComponent } from './voice-input.component';

export const STATUS_CONNECTED = 'Connected';
export const STATUS_DISCONNECTED = 'Disconnected';

@Component({
  selector: 'app-chat-container',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ChatHistoryComponent,
    VoiceInputComponent,
  ],
  templateUrl: './chat-container.component.html',
  styleUrl: './chat-container.component.scss',
})
export class ChatContainerComponent implements OnInit, OnDestroy {
  readonly STATUS_CONNECTED = STATUS_CONNECTED;
  readonly STATUS_DISCONNECTED = STATUS_DISCONNECTED;

  chatHistory = viewChild(ChatHistoryComponent);

  private api = inject(ApiService);
  private audioRecord = inject(AudioRecordService);
  private audioPlayback = inject(AudioPlaybackService);

  sessions = signal<Session[]>([]);
  currentSessionId = signal<string>('');
  currentSessionTitle = signal<string>('New Conversation');
  editingSessionId = signal<string | null>(null);
  editingTitle = signal<string>('');
  messages = signal<Message[]>([]);
  inputText = signal<string>('');

  isSidebarOpen = signal<boolean>(false);
  isConnected = signal<boolean>(false);
  readonly connectionStatus = computed(() =>
    this.isConnected() ? STATUS_CONNECTED : STATUS_DISCONNECTED
  );
  isStreaming = signal<boolean>(false);
  streamingText = signal<string>('');
  readonly isRecording = this.audioRecord.isRecording;
  readonly audioLevel = this.audioRecord.audioLevel;
  isProcessingVoice = signal<boolean>(false);
  isVadActive = signal<boolean>(false);
  private transcriptTimeout: any = null;
  private readonly transcriptTimeoutMs = 15000;
  healthInfo = signal<any>(null);
  sessionDocuments = signal<SessionDocument[]>([]);
  isUploadingFile = signal<boolean>(false);

  isLlmModalOpen = signal<boolean>(false);
  llmEngine = signal<string>('');
  llmBaseUrl = signal<string>('');
  llmModel = signal<string>('');
  llmApiKey = signal<string>('');
  llmHasApiKey = signal<boolean>(false);
  llmAuthPrompt = signal<string | null>(null);
  isSavingLlmSettings = signal<boolean>(false);

  readonly isSpeaking = this.audioPlayback.isPlaying;
  readonly isMuted = this.audioPlayback.isMuted;

  constructor() {
    effect(() => {
      const vad = this.isVadActive();
      const rec = this.isRecording();
      const proc = this.isProcessingVoice();
      if (vad && !rec && !proc) {
        this.restartVadIfActive();
      }
    });

    // React to speech onset detected signal for immediate audio barge-in
    effect(() => {
      const detected = this.audioRecord.speechDetected();
      if (detected > 0) {
        untracked(() => {
          this.handleBargeIn();
        });
      }
    });

    // React to end of a streamed utterance (audio frames were already sent while speaking)
    effect(() => {
      const ended = this.audioRecord.utteranceEnded();
      if (ended > 0) {
        untracked(() => {
          this.handleUtteranceEnd();
        });
      }
    });

    // React to WebSocket events queue signal
    effect(() => {
      const messages = this.api.wsMessages();
      if (messages.length > 0) {
        untracked(() => {
          const batch = this.api.drainWsMessages();
          for (const event of batch) {
            this.handleWsEvent(event);
          }
        });
      }
    });
  }

  toggleMute(): void {
    this.audioPlayback.toggleMute();
  }

  handleBargeIn(): void {
    if (this.audioPlayback.isPlaying() || this.isStreaming()) {
      this.audioPlayback.stopPlayback();
      if (this.isStreaming()) {
        const partialText = this.streamingText().trim();
        if (partialText) {
          this.messages.update((msgs) => [
            ...msgs,
            {
              session_id: this.currentSessionId(),
              role: 'assistant',
              text: partialText,
              timestamp: new Date().toISOString(),
            },
          ]);
          this.chatHistory()?.scrollToBottom(true);
        }
        this.isStreaming.set(false);
        this.streamingText.set('');
      }
      this.api.sendWsMessage({
        type: 'interrupt',
        session_id: this.currentSessionId(),
      });
    }
  }

  async ngOnInit() {
    try {
      if (typeof this.api.getLlmSettings === 'function') {
        const cfg = await this.api.getLlmSettings();
        this.applyLlmSettingsState(cfg);
        this.isConnected.set(true);
        if (cfg.auth_error) {
          this.openLlmSettingsModal(
            cfg.auth_message || 'An API Key is required by the LLM server. Please enter your API Key.'
          );
        }
      } else {
        const health = await this.api.getHealth();
        this.healthInfo.set(health);
        this.isConnected.set(true);
      }
    } catch (e) {
      console.warn('Backend not yet reachable', e);
    }

    await this.loadSessions();

    // Connect WebSocket for streaming
    this.api.connectWebSocket();
  }

  private applyLlmSettingsState(cfg: {
    engine: string;
    base_url: string;
    model: string;
    has_api_key: boolean;
  }): void {
    this.llmEngine.set(cfg.engine);
    this.llmBaseUrl.set(cfg.base_url);
    this.llmModel.set(cfg.model);
    this.llmHasApiKey.set(Boolean(cfg.has_api_key));
    this.healthInfo.set({ engine: cfg.engine, model: cfg.model, base_url: cfg.base_url });
  }

  openLlmSettingsModal(promptMessage: string | null = null): void {
    const info = this.healthInfo();
    if (info?.engine) this.llmEngine.set(info.engine);
    if (info?.base_url) this.llmBaseUrl.set(info.base_url);
    if (info?.model) this.llmModel.set(info.model);
    this.llmApiKey.set('');
    this.llmAuthPrompt.set(promptMessage);
    this.isLlmModalOpen.set(true);
  }

  closeLlmSettingsModal(): void {
    this.isLlmModalOpen.set(false);
    this.llmApiKey.set('');
    this.llmAuthPrompt.set(null);
  }

  async saveLlmSettings(): Promise<void> {
    const base_url = this.llmBaseUrl().trim();
    const model = this.llmModel().trim();
    if (!base_url || !model) return;

    this.isSavingLlmSettings.set(true);
    try {
      const payload: { engine: string; base_url: string; model: string; api_key?: string } = {
        engine: this.llmEngine(),
        base_url,
        model,
      };
      if (this.llmApiKey().trim()) {
        payload.api_key = this.llmApiKey().trim();
      }
      const updated = await this.api.updateLlmSettings(payload);
      this.applyLlmSettingsState(updated);
      this.llmApiKey.set('');
      if (updated.auth_error) {
        this.llmAuthPrompt.set(
          updated.auth_message || 'An API Key is required by the LLM server. Please enter your API Key.'
        );
      } else {
        this.closeLlmSettingsModal();
      }
    } catch (e: any) {
      this.llmAuthPrompt.set(e.message || 'Failed to save LLM configuration.');
    } finally {
      this.isSavingLlmSettings.set(false);
    }
  }

  ngOnDestroy() {
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
    this.chatHistory()?.scrollToBottom(true);

    // Load documents attached to this session
    try {
      const docs = await this.api.getSessionDocuments(sessionId);
      this.sessionDocuments.set(docs);
    } catch {
      this.sessionDocuments.set([]);
    }
  }

  startEditingSession(session: Session, event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    this.editingSessionId.set(session.session_id);
    this.editingTitle.set(session.title);
  }

  async saveSessionTitle(sessionId: string, event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    const newTitle = this.editingTitle().trim();
    this.editingSessionId.set(null);

    if (!newTitle) return;

    // Optimistically update local session list and header
    this.sessions.update((list) =>
      list.map((s) => (s.session_id === sessionId ? { ...s, title: newTitle } : s))
    );
    if (this.currentSessionId() === sessionId) {
      this.currentSessionTitle.set(newTitle);
    }

    try {
      await this.api.updateSession(sessionId, newTitle);
    } catch (e) {
      console.error('Failed to update session title:', e);
    }
  }

  cancelEditingSession(event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    this.editingSessionId.set(null);
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

  async sendText(customText?: string) {
    const text = (customText !== undefined ? customText : this.inputText()).trim();
    if (!text) return;
    if (customText === undefined) {
      this.inputText.set('');
    }

    // Preemptively stop ongoing playback if active
    if (this.audioPlayback.isPlaying()) {
      this.audioPlayback.stopPlayback();
    }

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
    this.chatHistory()?.scrollToBottom(true);

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
      if (this.isProcessingVoice()) {
        return;
      }
      if (this.isSpeaking() || this.isStreaming()) {
        this.audioPlayback.stopPlayback();
        if (this.isStreaming()) {
          this.isStreaming.set(false);
          this.streamingText.set('');
        }
        this.api.sendWsMessage({
          type: 'interrupt',
          session_id: this.currentSessionId(),
        });
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

  /** Utterance finished: the backend is transcribing the streamed audio; wait for its `transcript` event. */
  handleUtteranceEnd(): void {
    this.isProcessingVoice.set(true);
    this.clearTranscriptTimeout();
    this.transcriptTimeout = setTimeout(() => this.handleTranscript(null), this.transcriptTimeoutMs);
  }

  private clearTranscriptTimeout(): void {
    if (this.transcriptTimeout) {
      clearTimeout(this.transcriptTimeout);
      this.transcriptTimeout = null;
    }
  }

  /** `text` is the backend transcript, or null when it never arrived (timeout). */
  async handleTranscript(text: string | null) {
    if (!this.isProcessingVoice()) return;
    this.clearTranscriptTimeout();
    let shouldRestartVad = false;

    try {
      if (text === null) {
        console.error('STT error: transcript timed out');
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
      } else if (text.trim()) {
        this.isProcessingVoice.set(false);
        await this.sendText(text.trim());
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
    } finally {
      this.isProcessingVoice.set(false);
      if (shouldRestartVad) {
        await this.restartVadIfActive();
      }
    }
  }

  private async handleWsEvent(event: any) {
    if (event.type === 'transcript') {
      await this.handleTranscript(event.text ?? '');
    } else if (event.type === 'token') {
      if (this.isStreaming()) {
        this.streamingText.update((t) => t + event.token);
        this.chatHistory()?.scrollToBottom(true);
      }
    } else if (event.type === 'audio_sentence') {
      if (event.audio) {
        this.audioPlayback.enqueueBase64Wav(event.audio);
      }
    } else if (event.type === 'interrupted') {
      if (this.isStreaming()) {
        const partialText = this.streamingText().trim();
        if (partialText) {
          this.messages.update((msgs) => [
            ...msgs,
            {
              session_id: this.currentSessionId(),
              role: 'assistant',
              text: partialText,
              timestamp: new Date().toISOString(),
            },
          ]);
          this.chatHistory()?.scrollToBottom(true);
        }
      }
      this.isStreaming.set(false);
      this.streamingText.set('');
    } else if (event.type === 'done') {
      if (this.isStreaming()) {
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
        this.chatHistory()?.scrollToBottom(true);
        if (event.full_text?.includes('[Error: Authentication failed')) {
          this.openLlmSettingsModal('An API Key is required by the LLM server. Please enter your API Key.');
        }
      }

      if (this.isVadActive()) {
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
      this.chatHistory()?.scrollToBottom(true);
      await this.restartVadIfActive();
    }
  }

  private async restartVadIfActive() {
    if (this.isVadActive() && !this.isRecording() && !this.isProcessingVoice()) {
      try {
        await new Promise((r) => setTimeout(r, 100));
        if (this.isVadActive() && !this.isRecording() && !this.isProcessingVoice()) {
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
    if (this.isStreaming()) {
      const partialText = this.streamingText().trim();
      if (partialText) {
        this.messages.update((msgs) => [
          ...msgs,
          {
            session_id: this.currentSessionId(),
            role: 'assistant',
            text: partialText,
            timestamp: new Date().toISOString(),
          },
        ]);
        this.chatHistory()?.scrollToBottom(true);
      }
      this.isStreaming.set(false);
      this.streamingText.set('');
    }
    this.api.sendWsMessage({
      type: 'interrupt',
      session_id: this.currentSessionId(),
    });
  }

  triggerFileUpload(): void {
    const input = document.getElementById('doc-file-input') as HTMLInputElement;
    if (input) {
      input.click();
    }
  }

  async uploadFile(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    // Reset input so the same file can be re-uploaded
    input.value = '';

    const sessionId = this.currentSessionId();
    if (!sessionId) return;

    this.isUploadingFile.set(true);
    try {
      await this.api.uploadDocument(sessionId, file);
      const docs = await this.api.getSessionDocuments(sessionId);
      this.sessionDocuments.set(docs);

      // Show confirmation in chat
      this.messages.update((msgs) => [
        ...msgs,
        {
          session_id: sessionId,
          role: 'assistant',
          text: `Document "${file.name}" attached. I can now answer questions about its contents.`,
          timestamp: new Date().toISOString(),
        },
      ]);
      this.chatHistory()?.scrollToBottom(true);
    } catch (e: any) {
      this.messages.update((msgs) => [
        ...msgs,
        {
          session_id: sessionId,
          role: 'assistant',
          text: `Failed to upload "${file.name}": ${e.message || 'Unknown error'}`,
          is_error: true,
          timestamp: new Date().toISOString(),
        },
      ]);
      this.chatHistory()?.scrollToBottom(true);
    } finally {
      this.isUploadingFile.set(false);
    }
  }
}
