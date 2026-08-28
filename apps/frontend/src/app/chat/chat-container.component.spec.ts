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
    createSession: () => Promise.resolve({ session_id: 'test-1', title: 'Test Chat' }),
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
});
