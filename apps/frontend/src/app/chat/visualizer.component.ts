import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-visualizer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './visualizer.component.html',
  styleUrl: './visualizer.component.scss',
})
export class VisualizerComponent {
  isActive = input<boolean>(false);
  isSpeaking = input<boolean>(false);
  level = input<number>(0);
}
