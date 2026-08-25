# Task 015: Separate Component Templates/Styles/Tests & Configure Generator Defaults

- **Status**: Backlog
- **Target Component**: `apps/frontend/src/app/`, `nx.json`, `apps/frontend/project.json`
- **Instruction Reference**: [frontend-angular.md](../../instructions/frontend-angular.md)

## Objective
Enforce clean component architecture by extracting inline templates and SCSS styles into dedicated `.html`, `.scss`, and `.spec.ts` files, and configure the Angular component generator defaults in NX so all future components automatically follow this pattern:

1. **Extract Existing Inline Components to Dedicated Files**:
   - For `ChatContainerComponent`:
     - Extract template to `apps/frontend/src/app/chat/chat-container.component.html` (`templateUrl`).
     - Extract styling to `apps/frontend/src/app/chat/chat-container.component.scss` (`styleUrls` or `styleUrl`).
     - Create unit test spec `apps/frontend/src/app/chat/chat-container.component.spec.ts`.
   - For `ChatHistoryComponent`:
     - Extract to `chat-history.component.html`, `chat-history.component.scss`, and `chat-history.component.spec.ts`.
   - For `VoiceInputComponent`:
     - Extract to `voice-input.component.html`, `voice-input.component.scss`, and `voice-input.component.spec.ts`.
   - For `VisualizerComponent`:
     - Extract to `visualizer.component.html`, `visualizer.component.scss`, and `visualizer.component.spec.ts`.
   - For `AppComponent`:
     - Extract to `app.component.html`, `app.component.scss`, and `app.component.spec.ts` (if applicable).

2. **Configure NX Generators Defaults**:
   - In `nx.json` (under `generators`), configure `@nx/angular:component` defaults:
     ```json
     "generators": {
       "@nx/angular:component": {
         "style": "scss",
         "inlineTemplate": false,
         "inlineStyle": false,
         "skipTests": false
       }
     }
     ```
   - Ensure any future components generated via `bunx nx generate @nx/angular:component ...` automatically generate independent `.html`, `.scss`, `.ts`, and `.spec.ts` files.
