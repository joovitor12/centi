# Centi Frontend

Frontend React application for the Centi calendar assistant.

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create `.env` file (optional, defaults work for local development):
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_PARLANT_SERVER_URL=http://localhost:8800
REACT_APP_PARLANT_AGENT_ID=default
```

3. Start development server:
```bash
npm start
```

The app will run on `http://localhost:3000`.

## Building for Production

```bash
npm run build
```

This creates a `build` directory with optimized production files. The backend (`run_production.py`) will automatically serve these files when deployed.

## Features

- **Authentication**: Google OAuth login
- **Chat Interface**: Integrated Parlant chat widget
- **Session Management**: Automatic session creation and persistence
- **User Context**: Each user gets their own Parlant session with access to their calendar

## Architecture

- **Components**: React components for Login, Chat, and Loading states
- **Services**: API client and authentication service
- **Types**: TypeScript type definitions

The frontend communicates with the backend FastAPI server for authentication and session management, and connects directly to the Parlant server for chat functionality.

