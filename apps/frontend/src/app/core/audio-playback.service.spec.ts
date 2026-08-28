import { TestBed } from '@angular/core/testing';
import { AudioPlaybackService } from './audio-playback.service';

describe('AudioPlaybackService', () => {
  let service: AudioPlaybackService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AudioPlaybackService],
    });
    service = TestBed.inject(AudioPlaybackService);
  });

  it('should be created with initial playing false and muted false signals', () => {
    expect(service).toBeTruthy();
    expect(service.isPlaying()).toBe(false);
    expect(service.isMuted()).toBe(false);
  });

  it('should toggle and set mute state reactively via signals', () => {
    const nextState = service.toggleMute();
    expect(nextState).toBe(true);
    expect(service.isMuted()).toBe(true);

    service.setMuted(false);
    expect(service.isMuted()).toBe(false);

    service.setMuted(true);
    expect(service.isMuted()).toBe(true);
  });

  it('should immediately stop playback and clear queue when muted', () => {
    const stopSpy = vi.spyOn(service, 'stopPlayback');
    service.setMuted(true);
    expect(stopSpy).toHaveBeenCalled();
    expect(service.isPlaying()).toBe(false);
  });

  it('should discard enqueueBase64Wav calls when muted', async () => {
    service.setMuted(true);
    // Passing valid base64 data
    const dummyB64 = btoa('test audio data');
    await service.enqueueBase64Wav(dummyB64);
    expect(service.isPlaying()).toBe(false);
  });

  it('should discard enqueueWavBlob calls when muted', async () => {
    service.setMuted(true);
    const blob = new Blob(['test audio'], { type: 'audio/wav' });
    await service.enqueueWavBlob(blob);
    expect(service.isPlaying()).toBe(false);
  });
});
