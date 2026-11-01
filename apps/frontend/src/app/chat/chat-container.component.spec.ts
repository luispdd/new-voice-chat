import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { By } from '@angular/platform-browser';
import { ChatContainerComponent } from './chat-container.component';
import { ApiService } from '../core/api.service';
import { AudioRecordService } from '../core/audio-record.service';
import { AudioPlaybackService } from '../core/audio-playback.service';

describe('ChatContainerComponent', () => {
  let component: ChatContainerComponent;
  let fixture: ComponentFixture<ChatContainerComponent>;

  const isPlayingSig = signal(false);
  const isMutedSig = signal(false);
  const isRecordingSig = signal(false);
  const audioLevelSig = signal(0);
  const speechDetectedSig = signal(0);
  const utteranceEndedSig = signal(0);
  const wsMessagesSig = signal<any[]>([]);

  const mockApiService = {
    getHealth: () => Promise.resolve({ engine: 'ollama', model: 'llama3' }),
    getSessions: () => Promise.resolve([]),
    createSession: (title = 'New Conversation') => Promise.resolve({ session_id: 'test-1', title }),
    updateSession: (sessionId: string, title: string) => Promise.resolve({ session_id: sessionId, title }),
    deleteSession: (sessionId: string) => Promise.resolve({ status: 'deleted', session_id: sessionId }),
    getMessages: () => Promise.resolve([]),
    wsMessages: wsMessagesSig.asReadonly(),
    drainWsMessages: () => {
      const msgs = wsMessagesSig();
      wsMessagesSig.set([]);
      return msgs;
    },
    connectWebSocket: vi.fn(),
    closeWebSocket: () => {},
    sendWsMessage: vi.fn(),
  };

  const mockAudioRecordService = {
    isRecording: isRecordingSig.asReadonly(),
    audioLevel: audioLevelSig.asReadonly(),
    utteranceEnded: utteranceEndedSig.asReadonly(),
    speechDetected: speechDetectedSig.asReadonly(),
    startRecording: () => Promise.resolve(),
    stopRecording: () => Promise.resolve(),
  };

  const mockAudioPlaybackService = {
    isPlaying: isPlayingSig.asReadonly(),
    isMuted: isMutedSig.asReadonly(),
    toggleMute: vi.fn(() => {
      isMutedSig.set(!isMutedSig());
      return isMutedSig();
    }),
    setMuted: vi.fn((muted: boolean) => isMutedSig.set(muted)),
    stopPlayback: vi.fn(),
  };

  beforeEach(async () => {
    isPlayingSig.set(false);
    isMutedSig.set(false);
    isRecordingSig.set(false);
    audioLevelSig.set(0);
    speechDetectedSig.set(0);
    utteranceEndedSig.set(0);
    wsMessagesSig.set([]);

    await TestBed.configureTestingModule({
      imports: [ChatContainerComponent],
      providers: [
        { provide: ApiService, useValue: mockApiService },
        { provide: AudioRecordService, useValue: mockAudioRecordService },
        { provide: AudioPlaybackService, useValue: mockAudioPlaybackService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ChatContainerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should create a new session and select it', async () => {
    await component.createNewSession();
    expect(component.sessions().length).toBeGreaterThan(0);
    expect(component.currentSessionId()).toBe('test-1');
  });

  it('should start editing and save session title', async () => {
    const session = { session_id: 's-1', user_id: 'default_user', title: 'Initial Title', created_at: '', last_active: '' };
    component.sessions.set([session]);
    component.currentSessionId.set('s-1');

    component.startEditingSession(session);
    expect(component.editingSessionId()).toBe('s-1');
    expect(component.editingTitle()).toBe('Initial Title');

    component.editingTitle.set('Updated Title');
    await component.saveSessionTitle('s-1');

    expect(component.editingSessionId()).toBeNull();
    expect(component.sessions()[0].title).toBe('Updated Title');
    expect(component.currentSessionTitle()).toBe('Updated Title');
  });

  it('should cancel editing session title', () => {
    const session = { session_id: 's-1', user_id: 'default_user', title: 'Initial Title', created_at: '', last_active: '' };
    component.startEditingSession(session);
    expect(component.editingSessionId()).toBe('s-1');

    component.cancelEditingSession();
    expect(component.editingSessionId()).toBeNull();
  });

  it('should delete a session and select remaining session', async () => {
    const session1 = { session_id: 's-1', user_id: 'default_user', title: 'Session 1', created_at: '', last_active: '' };
    const session2 = { session_id: 's-2', user_id: 'default_user', title: 'Session 2', created_at: '', last_active: '' };
    component.sessions.set([session1, session2]);
    component.currentSessionId.set('s-1');

    const fakeEvent = { stopPropagation: () => {} } as unknown as Event;
    await component.deleteSession('s-1', fakeEvent);

    expect(component.sessions().length).toBe(1);
    expect(component.sessions()[0].session_id).toBe('s-2');
    expect(component.currentSessionId()).toBe('s-2');
  });

  it('should render toolbar mute toggle button and toggle mute on click', () => {
    isMutedSig.set(false);
    fixture.detectChanges();

    const muteBtn = fixture.debugElement.query(By.css('.mute-toggle-btn'));
    expect(muteBtn).toBeTruthy();
    expect(muteBtn.nativeElement.classList.contains('muted')).toBe(false);

    const icon = muteBtn.query(By.css('i'));
    expect(icon.nativeElement.className).toContain('pi-volume-up');

    muteBtn.nativeElement.click();
    fixture.detectChanges();

    expect(mockAudioPlaybackService.toggleMute).toHaveBeenCalled();
    expect(component.isMuted()).toBe(true);
    expect(muteBtn.nativeElement.classList.contains('muted')).toBe(true);
    expect(icon.nativeElement.className).toContain('pi-volume-off');
  });

  it('should trigger barge-in when speech is detected during playback and preserve partial text', () => {
    isPlayingSig.set(true);
    component.currentSessionId.set('test-session-123');
    component.isStreaming.set(true);
    component.streamingText.set('Partial response before barge in');
    fixture.detectChanges();

    // Trigger speech onset signal
    speechDetectedSig.update((c) => c + 1);
    fixture.detectChanges();

    expect(mockAudioPlaybackService.stopPlayback).toHaveBeenCalled();
    expect(component.isStreaming()).toBe(false);
    expect(component.messages().some((m) => m.text === 'Partial response before barge in')).toBe(true);
    expect(mockApiService.sendWsMessage).toHaveBeenCalledWith({
      type: 'interrupt',
      session_id: 'test-session-123',
    });
  });

  it('should wait for the backend transcript when a streamed utterance ends, then send it as text', async () => {
    component.currentSessionId.set('test-session-123');

    utteranceEndedSig.set(1);
    fixture.detectChanges();
    expect(component.isProcessingVoice()).toBe(true);

    wsMessagesSig.set([{ type: 'transcript', text: 'mock transcribed text' }]);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.isProcessingVoice()).toBe(false);
    expect(mockApiService.sendWsMessage).toHaveBeenCalledWith({
      type: 'text',
      session_id: 'test-session-123',
      text: 'mock transcribed text',
    });
  });

  it('should show a no-speech message when the transcript is empty', async () => {
    utteranceEndedSig.set(1);
    fixture.detectChanges();

    wsMessagesSig.set([{ type: 'transcript', text: '' }]);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.isProcessingVoice()).toBe(false);
    expect(component.messages().some((m) => m.text.includes('No speech detected'))).toBe(true);
  });

  it('should stop speech playback and preserve streaming text on stopSpeechPlayback', () => {
    component.currentSessionId.set('test-session-123');
    component.isStreaming.set(true);
    component.streamingText.set('Partial text on manual stop');

    component.stopSpeechPlayback();

    expect(mockAudioPlaybackService.stopPlayback).toHaveBeenCalled();
    expect(component.isStreaming()).toBe(false);
    expect(component.messages().some((m) => m.text === 'Partial text on manual stop')).toBe(true);
    expect(mockApiService.sendWsMessage).toHaveBeenCalledWith({
      type: 'interrupt',
      session_id: 'test-session-123',
    });
  });

  it('should react to wsMessages token and done signals via effect', () => {
    component.currentSessionId.set('test-session-123');
    component.isStreaming.set(true);
    fixture.detectChanges();

    // Stream token event
    wsMessagesSig.set([{ type: 'token', token: 'Hello' }]);
    fixture.detectChanges();
    expect(component.streamingText()).toBe('Hello');

    // Stream done event
    wsMessagesSig.set([{ type: 'done', full_text: 'Hello world!' }]);
    fixture.detectChanges();
    expect(component.isStreaming()).toBe(false);
    expect(component.messages().some((m) => m.text === 'Hello world!')).toBe(true);
  });

  it('should enqueue audio_sentence even when sent in a batch with a subsequent token without dropping audio', () => {
    const enqueueSpy = vi.spyOn(mockAudioPlaybackService, 'stopPlayback'); // verify mock exists
    (mockAudioPlaybackService as any).enqueueBase64Wav = vi.fn();
    component.currentSessionId.set('test-session-123');
    component.isStreaming.set(true);
    fixture.detectChanges();

    // Both audio_sentence and token arrive in the same batch
    wsMessagesSig.set([
      { type: 'audio_sentence', sentence: 'Got it.', audio: 'fake-wav-base64' },
      { type: 'token', token: " I'm" },
    ]);
    fixture.detectChanges();

    expect((mockAudioPlaybackService as any).enqueueBase64Wav).toHaveBeenCalledWith('fake-wav-base64');
    expect(component.streamingText()).toBe(" I'm");
  });

  it('should preemptively stop playback and stream new query on sendText', async () => {
    isPlayingSig.set(true);
    component.currentSessionId.set('test-session-123');
    component.inputText.set('New query after barge-in');

    await component.sendText();

    expect(mockAudioPlaybackService.stopPlayback).toHaveBeenCalled();
    expect(component.isStreaming()).toBe(true);
    expect(mockApiService.sendWsMessage).toHaveBeenCalledWith({
      type: 'text',
      session_id: 'test-session-123',
      text: 'New query after barge-in',
    });
  });
});
