import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatContainerComponent } from './chat/chat-container.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ChatContainerComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {}

