import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    telegram_bot_token: str
    groq_api_key: str
    gemini_api_key: str
    openai_api_key: str
    gmail_address: str
    gmail_app_password: str
    my_telegram_user_id: int
    serper_api_key: str
    my_name: str
    company_name: str
    my_role: str
    my_one_liner: str

def load_config() -> Config:
    required = {
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "MY_TELEGRAM_USER_ID": os.getenv("MY_TELEGRAM_USER_ID"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"[FATAL] Missing required env vars: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in all values.")
        exit(1)

    return Config(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        gemini_api_key=os.getenv("GOOGLE_GEMINI_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        gmail_address=os.getenv("GMAIL_ADDRESS", ""),
        gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", ""),
        my_telegram_user_id=int(os.getenv("MY_TELEGRAM_USER_ID", "0")),
        serper_api_key=os.getenv("SERPER_API_KEY", ""),
        my_name=os.getenv("MY_NAME", "Founder"),
        company_name=os.getenv("MY_COMPANY_NAME", "My Company"),
        my_role=os.getenv("MY_ROLE", "Founder"),
        my_one_liner=os.getenv("MY_ONE_LINER", ""),
    )

config = load_config()
