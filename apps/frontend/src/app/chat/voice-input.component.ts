import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-voice-input',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './voice-input.component.html',
  styleUrl: './voice-input.component.scss',
})
export class VoiceInputComponent {
  isRecording = input<boolean>(false);
  isProcessing = input<boolean>(false);
  disabled = input<boolean>(false);
  onToggleMic = output<void>();
}
