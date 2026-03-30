# EmoSync — Frontend

The Next.js frontend for EmoSync, an AI-powered emotional wellness coach. Provides a chat interface with text and voice input, a collapsible sidebar, dark/light mode, and authentication pages.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| [Next.js 16](https://nextjs.org) (App Router) | Framework |
| [React 19](https://react.dev) | UI library |
| [TypeScript](https://www.typescriptlang.org) | Type safety |
| [Tailwind CSS v4](https://tailwindcss.com) | Styling |
| [shadcn/ui](https://ui.shadcn.com) (Radix/Nova preset) | Component library |
| [Lucide React](https://lucide.dev) | Icons |
| [next-themes](https://github.com/pacocoursey/next-themes) | Dark/light mode |

---

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout with ThemeProvider
│   ├── page.tsx                # Landing page with chat interface
│   ├── globals.css             # Global styles and CSS variables
│   └── auth/
│       ├── login/page.tsx      # Login page
│       └── register/page.tsx   # Registration page
├── components/
│   ├── sidebar.tsx             # Collapsible sidebar
│   ├── theme-provider.tsx      # next-themes wrapper
│   └── ui/
│       └── button.tsx          # shadcn Button component
├── hooks/
│   └── use-audio-recorder.ts   # MediaRecorder hook for voice input
├── lib/
│   ├── mock-audio-service.ts   # Mock STT/TTS (browser SpeechSynthesis)
│   └── utils.ts                # Tailwind class merge utility
└── public/
    └── logo.ico                # App logo
```

---

## Getting Started

### Prerequisites

- Node.js 18 or later
- npm

### Install dependencies

```bash
npm install
```

### Run the development server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

The page hot-reloads automatically as you edit files.

---

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server at http://localhost:3000 |
| `npm run build` | Build the app for production |
| `npm start` | Run the production build |
| `npm run lint` | Run ESLint |

---

## Key Features

### Chat Interface
- Text and voice input on the landing page
- Simulated AI responses with typing indicator
- Voice messages recorded via the browser `MediaRecorder` API
- Mock speech-to-text (fake transcription) and text-to-speech (browser `SpeechSynthesis`)

> **Note:** The voice pipeline currently uses mock implementations. When the Flask backend is connected, `lib/mock-audio-service.ts` will be replaced with real API calls to Whisper (STT) and ElevenLabs (TTS).

### Sidebar
- Collapsible — expands to show labels, collapses to icon-only
- Links: New Chat, Search Chats, Your Chats (when logged in), Help, Subscription

### Auth Pages
- `/auth/login` — email + password login, show/hide password toggle, "Forgot password?" link
- `/auth/register` — name, email, password with live validation rules, confirm password mismatch detection

> Both auth pages show mock error messages. Real authentication requires the Flask backend.

### Theme
- System, light, and dark mode via `next-themes`
- Toggle button in the top-right header

---

## Environment Variables

No environment variables are required to run the frontend in mock mode.

When the Flask backend is available, create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Backend

The Flask backend (in `../backend/`) handles authentication, chat, speech-to-text, and text-to-speech. See the root [execution.md](../execution.md) for the full project plan.
