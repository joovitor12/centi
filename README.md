# Centi - Smart Calendar Assistant 🤖

A professional AI assistant powered by [Parlant](https://parlant.ai/) that helps you manage appointments and reminders with natural language intelligence.

## 🌟 Features

- **Natural Language Scheduling**: Schedule appointments using phrases like "remind me to call mom in 2 hours" or "meeting tomorrow at 3pm"
- **Intelligent Time Parsing**: Automatically converts relative time expressions to precise timestamps
- **Recurring Appointments**: Create repeating appointments (daily, weekly, monthly) with automatic Google Calendar sync
- **Smart Calendar Management**: View, add, edit, and manage your appointments seamlessly
- **Google Calendar Integration**: Automatic bidirectional sync with Google Calendar
- **Conversational Interface**: Interact naturally with your AI assistant like Jarvis from Iron Man

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- Supabase account and project
- Google Cloud project with Calendar API enabled (optional, for Google Calendar sync)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/joovitor12/centi.git
cd centi
```

2. Install dependencies:
```bash
uv install
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
GOOGLE_CREDENTIALS_PATH=.credentials/credentials.json
GOOGLE_CALENDAR_ID=your-email@gmail.com
GOOGLE_CALENDAR_TIMEZONE=America/Sao_Paulo
```

4. Run the application:
```bash
uv run python main.py
```

5. Open the Sandbox UI: http://localhost:8800

## 🏢 Organization Setup (Email Interactor)

For installing Centi as an app in an organization, you can provide a pre-generated OAuth token instead of going through the interactive OAuth flow. This is useful for automated deployments and organizational installations.

### Configuration for Organizations

1. **Generate OAuth Token**: Use Google's OAuth 2.0 flow to generate a token with the required scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/gmail.modify`

2. **Create Token File**: Save the token as a JSON file in the standard Google OAuth format:
   ```json
   {
     "token": "ya29.a0...",
     "refresh_token": "1//0g...",
     "token_uri": "https://oauth2.googleapis.com/token",
     "client_id": "...",
     "client_secret": "...",
     "scopes": [
       "https://www.googleapis.com/auth/calendar",
       "https://www.googleapis.com/auth/gmail.modify"
     ]
   }
   ```

3. **Configure Environment Variables**: Add to your `.env` file:
   ```env
   # Email address for Centi agent (its own mailbox)
   CENTI_EMAIL_ADDRESS=centi@yourorg.com
   
   # Path to pre-generated OAuth token file
   GOOGLE_TOKEN_PATH=/path/to/token.json
   
   # Calendar owner email (the person whose calendar Centi will manage)
   GOOGLE_CALENDAR_ID=owner@yourorg.com
   
   # Gmail polling interval (optional, defaults to 120 seconds)
   GMAIL_POLL_INTERVAL_SECONDS=120
   ```

### Authentication Priority

The system uses the following priority order for authentication:
1. **GOOGLE_TOKEN_JSON** (environment variable) → Token JSON as string (recommended for cloud deployments)
2. **GOOGLE_TOKEN_PATH** (file path) → Uses the pre-generated token directly
3. **GOOGLE_CREDENTIALS_JSON** (environment variable) → Credentials JSON as string
4. **GOOGLE_CREDENTIALS_PATH** (file path) → Starts interactive OAuth flow (only works locally)
5. None → Disables Google integration

### Security Notes

- **Token files are sensitive**: Treat them as secrets and never commit them to version control
- **Scoped access**: Centi uses its own mailbox (`CENTI_EMAIL_ADDRESS`) and only has calendar access for the specified owner
- **Privacy**: Centi only processes emails when explicitly CC'd into threads (first message requires CC, subsequent replies accept TO or CC)

### Cloud Deployment (Render, etc.)

For cloud deployments where you can't use local files, you can provide credentials via environment variables:

```env
# Instead of GOOGLE_TOKEN_PATH, use GOOGLE_TOKEN_JSON with the full token JSON as a string
GOOGLE_TOKEN_JSON={"token":"ya29.a0...","refresh_token":"1//0g...",...}

# Same for credentials (though GOOGLE_TOKEN_JSON is recommended)
GOOGLE_CREDENTIALS_JSON={"token":"...","refresh_token":"...",...}
```

**Full deployment guide**: See [`docs/deploy_render.md`](docs/deploy_render.md) for detailed instructions on deploying to Render and other cloud platforms.

## 💬 Usage Examples

**Schedule an appointment:**
```
User: "Schedule a dentist appointment for tomorrow at 2pm"
Centi: ✅ 'dentist appointment' scheduled for November 15, 2025 at 02:00 PM
```

**Set a reminder:**
```
User: "Remind me to take out the trash in 30 minutes"
Centi: ✅ 'take out the trash' scheduled for November 14, 2025 at 03:30 PM
```

**View your schedule:**
```
User: "What do I have scheduled today?"
Centi: Here are your appointments for today...
```

**Create a recurring appointment:**
```
User: "Remind me to exercise every Monday, Wednesday, and Friday at 7am"
Centi: ✅ Recurring appointment 'exercise' created. First occurrence: December 02, 2025 at 07:00 AM
```

**Create a daily reminder:**
```
User: "Daily reminder to take vitamins at 8am"
Centi: ✅ Recurring appointment 'take vitamins' created. First occurrence: November 27, 2025 at 08:00 AM
```

## 🏗️ Architecture

This project showcases **best practices** for building conversational AI with Parlant:

### Core Principles

1. **Separation of Concerns**: Business logic (datetime parsing) is handled by the LLM, while code focuses on validation and data persistence
2. **Dynamic Context**: Guidelines receive real-time context (current datetime) for accurate calculations
3. **Smart Tool Design**: Simple tools that trust the LLM's natural language understanding capabilities

### Key Components

- **Guidelines**: Define when and how tools should be used with dynamic context
- **Tools**: Clean, focused functions for appointment management
- **Natural Language Processing**: LLM handles complex time calculations and format conversions

## 🔧 Technical Details

### Database Schema

```sql
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    time TIMESTAMP NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### Time Parsing Examples

The AI assistant automatically converts natural language to precise timestamps:

- "in 3 hours" → `2025-11-14 17:30:00`
- "tomorrow at 4:30pm" → `2025-11-15 16:30:00`
- "next Monday at 9am" → `2025-11-18 09:00:00`

### Recurring Appointment Examples

The assistant automatically detects and creates recurring appointments:

- "every day" / "daily" → Creates daily recurring appointment
- "every Monday" / "Mondays" → Creates weekly recurring appointment on Mondays
- "every Monday and Wednesday" → Creates weekly recurring appointment on both days
- "every month" / "monthly" → Creates monthly recurring appointment
- "every 15th of the month" → Creates monthly recurring appointment on the 15th

## 🛠️ Development

### Project Structure

```
centi/
├── main.py              # Main application entry point
├── app/                 # Application package
│   ├── config/          # Configuration and settings
│   │   └── settings.py  # Environment variables and settings
│   ├── services/        # External services
│   │   └── supabase_service.py      # Supabase database service
│   ├── tools/           # Parlant tools
│   │   └── appointments.py  # Appointment management tools
│   └── agent/           # Agent configuration
│       └── guidelines.py # Agent guidelines
├── alembic/             # Database migrations
├── parlant-data/        # Parlant cache and embeddings
└── README.md
```

See `app/README.md` for detailed architecture documentation.

## 📈 Roadmap

- [x] Natural language appointment scheduling
- [x] Intelligent time parsing
- [x] Calendar management
- [x] Google Calendar integration
- [x] Recurring appointments
- [ ] Email notifications
- [ ] Multi-timezone support
