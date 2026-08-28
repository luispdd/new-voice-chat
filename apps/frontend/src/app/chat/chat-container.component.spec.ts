import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, Subject } from 'rxjs';
import { ChatContainerComponent } from './chat-container.component';
import { ApiService } from '../core/api.service';
import { AudioRecordService } from '../core/audio-record.service';
import { AudioPlaybackService } from '../core/audio-playback.service';

describe('ChatContainerComponent', () => {
  let component: ChatContainerComponent;
  let fixture: ComponentFixture<ChatContainerComponent>;

  const mockApiService = {
    getHealth: () => Promise.resolve({ engine: 'ollama', model: 'llama3' }),
    getSessions: () => Promise.resolve([]),
    createSession: (title = 'New Conversation') => Promise.resolve({ session_id: 'test-1', title }),
    updateSession: (sessionId: string, title: string) => Promise.resolve({ session_id: sessionId, title }),
    deleteSession: (sessionId: string) => Promise.resolve({ status: 'deleted', session_id: sessionId }),
    getMessages: () => Promise.resolve([]),
    connectWebSocket: () => of({}),
    closeWebSocket: () => {},
  };

  const mockAudioRecordService = {
    isRecording: of(false),
    audioLevel: of(0),
    onAudioChunkReady: new Subject<Blob>(),
    startRecording: () => Promise.resolve(),
    stopRecording: () => Promise.resolve(),
  };

  const mockAudioPlaybackService = {
    isPlaying: of(false),
    stopPlayback: () => {},
  };

  beforeEach(async () => {
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
});
