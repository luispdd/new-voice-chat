import { Routes } from '@angular/router';
import { ChatContainerComponent } from './chat/chat-container.component';

export const routes: Routes = [
  { path: '', component: ChatContainerComponent },
  { path: '**', redirectTo: '' },
];
