# Founder OS — Personal AI Executive Assistant

Runs locally on your machine. Interface is Telegram. Free except LLM API calls (~₹100-200/month).

## Setup

1. Clone and enter the project
2. Create a virtual environment: `python -m venv venv && source venv/bin/activate` (Windows: `py -m venv venv && venv\Scripts\activate`)
3. Install dependencies: `pip install -r requirements.txt`
4. Copy config: `cp .env.example .env` (Windows: `copy .env.example .env`)
5. Fill in all values in `.env`
6. Run: `python main.py`

## Usage

Send messages to your Telegram bot:
- `research [company name]` — full company intelligence
- `draft email to [name] at [company]` — personalized outreach
- `add [name] from [company]` — add to CRM
- `mark [name] as responded` — update CRM status
- `who do I need to follow up with` — pending follow-ups
- `show pipeline` — pipeline summary
- `daily report` — full daily briefing
- `note: [anything]` — save to memory
- `search [query]` — search memory
- `todo: [task]` — add a task

## LLM Routing
- Groq (free) → Gemini Flash (free) → OpenAI GPT-4o-mini (paid fallback)

## Architecture
See the system diagram in the project documentation.
