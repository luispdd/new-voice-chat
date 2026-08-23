import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-voice-input',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="voice-controls">
      <button
        class="mic-button"
        [ngClass]="{ recording: isRecording, processing: isProcessing }"
        (click)="onToggleMic.emit()"
        [title]="isRecording ? 'Click to stop recording' : 'Click to talk (VAD active)'"
      >
        <i class="pi" [ngClass]="isRecording ? 'pi-stop-circle' : 'pi-microphone'"></i>
      </button>

      <span *ngIf="isRecording" class="recording-label">Listening...</span>
      <span *ngIf="isProcessing" class="recording-label">Processing voice...</span>
    </div>
  `,
  styles: [`
    .voice-controls {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .mic-button {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      border: none;
      background: linear-gradient(135deg, #0284c7, #0369a1);
      color: #ffffff;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
      transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
      box-shadow: 0 4px 15px rgba(2, 132, 199, 0.3);

      &:hover {
        transform: scale(1.08);
        box-shadow: 0 6px 20px rgba(2, 132, 199, 0.5);
      }

      &.recording {
        background: linear-gradient(135deg, #e11d48, #be123c);
        box-shadow: 0 0 20px rgba(225, 29, 72, 0.6);
        animation: pulse-mic 1.5s infinite;
      }

      &.processing {
        background: linear-gradient(135deg, #a855f7, #7e22ce);
      }
    }

    .recording-label {
      font-size: 0.85rem;
      color: var(--accent-cyan);
      font-weight: 500;
      animation: fade-in-out 1.5s infinite;
    }

    @keyframes pulse-mic {
      0% { transform: scale(1); }
      50% { transform: scale(1.1); }
      100% { transform: scale(1); }
    }

    @keyframes fade-in-out {
      0%, 100% { opacity: 0.6; }
      50% { opacity: 1; }
    }
  `],
})
export class VoiceInputComponent {
  @Input() isRecording = false;
  @Input() isProcessing = false;
  @Output() onToggleMic = new EventEmitter<void>();
}
