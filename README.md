# Centi - Smart Calendar Assistant 🤖

A professional AI assistant powered by [Parlant](https://parlant.ai/) that helps you manage appointments and reminders with natural language intelligence.

## 🌟 Features

- **Natural Language Scheduling**: Schedule appointments using phrases like "remind me to call mom in 2 hours" or "meeting tomorrow at 3pm"
- **Intelligent Time Parsing**: Automatically converts relative time expressions to precise timestamps
- **Smart Calendar Management**: View, add, and manage your appointments seamlessly
- **Conversational Interface**: Interact naturally with your AI assistant like Jarvis from Iron Man

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- Supabase account and project

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
```

4. Run the application:
```bash
uv run python main.py
```

5. Open the Sandbox UI: http://localhost:8800

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
- [ ] Google Calendar integration
- [ ] Recurring appointments
- [ ] Email notifications
- [ ] Multi-timezone support
