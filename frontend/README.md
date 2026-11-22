# Sky Reader frontend

The React and Vite workspace provides weather chat, city lookup, account and guest access, weather atmosphere preferences, and evidence and risk views. See the [root README](../README.md) for setup and architecture.

`src/App.jsx` composes the workspace. `src/utils/authSession.js`, `chatThreads.js`, and `conversations.js` handle authentication state, server thread revisions, and browser transcripts. `src/components/ChatMessage.jsx` renders the response and available audit or risk details.

The checked-in API origin is `http://127.0.0.1:8000`. Start the backend and use Vite on port 5173. The browser does not require provider credentials.

```bash
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
npm test
npm run lint
npm run build
```
