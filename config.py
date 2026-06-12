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
    public_access: bool          # if true, ANY Telegram user can use the bot
    serper_api_key: str
    tavily_api_key: str
    my_name: str
    company_name: str
    my_role: str
    my_one_liner: str
    # Autonomy / agent
    auto_approve: bool
    heartbeat_hours: int
    autonomy_level: str          # cautious | balanced | autonomous
    voice_replies: bool          # speak responses back to voice messages
    web_ui_enabled: bool         # primary web UI (chat + full dashboard)
    telegram_enabled: bool       # optional Telegram bot channel
    dashboard_enabled: bool      # alias for web_ui_enabled (legacy)
    dashboard_port: int
    daily_llm_call_cap: int      # 0 = unlimited
    agent_paused: bool           # kill switch

    # Local model (Ollama) + caching
    ollama_enabled: bool
    ollama_base_url: str
    ollama_model: str
    semantic_cache: bool
    cache_distance_threshold: float
    # Tool-RAG: retrieve only the most relevant tools per turn instead of all of them
    tool_rag: bool
    tool_rag_k: int
    # Google Calendar (optional)
    google_credentials_path: str
    google_token_path: str
    # X / Twitter (optional)
    x_api_key: str
    x_api_secret: str
    x_access_token: str
    x_access_token_secret: str
    x_bearer_token: str
    # Qdrant Cloud vector memory
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_prefix: str
    # GitHub (optional — world repo linking)
    github_client_id: str
    github_client_secret: str
    github_token_path: str
    github_redirect_uri: str
    public_base_url: str
    behind_proxy: bool
    dashboard_pin: str
    flask_secret_key: str

def _truthy(val: str, default: bool = False) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def load_config() -> Config:
    missing = []
    web_ui_enabled = _truthy(os.getenv("WEB_UI_ENABLED"), default=True)
    telegram_enabled = _truthy(os.getenv("TELEGRAM_ENABLED"), default=False)

    if telegram_enabled:
        if not os.getenv("TELEGRAM_BOT_TOKEN"):
            missing.append("TELEGRAM_BOT_TOKEN")
        if not os.getenv("MY_TELEGRAM_USER_ID"):
            missing.append("MY_TELEGRAM_USER_ID")

    if not web_ui_enabled and not telegram_enabled:
        missing.append("at least one of WEB_UI_ENABLED or TELEGRAM_ENABLED must be true")

    # At least one LLM provider key is required. Any one is enough — the router
    # falls back across whatever is configured (Groq -> Gemini -> OpenAI).
    llm_keys = [
        os.getenv("GROQ_API_KEY"),
        os.getenv("GOOGLE_GEMINI_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
    ]
    if not any(llm_keys):
        missing.append("at least one of GROQ_API_KEY / GOOGLE_GEMINI_API_KEY / OPENAI_API_KEY")
    if not os.getenv("QDRANT_URL"):
        missing.append("QDRANT_URL")
    if not os.getenv("QDRANT_API_KEY"):
        missing.append("QDRANT_API_KEY")

    if missing:
        print(f"[FATAL] Missing required env vars: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in the required values.")
        exit(1)

    return Config(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        gemini_api_key=os.getenv("GOOGLE_GEMINI_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        gmail_address=os.getenv("GMAIL_ADDRESS", ""),
        gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", ""),
        my_telegram_user_id=int(os.getenv("MY_TELEGRAM_USER_ID") or "0"),
        public_access=os.getenv("PUBLIC_ACCESS", "false").strip().lower() in ("1", "true", "yes", "on"),
        serper_api_key=os.getenv("SERPER_API_KEY", ""),
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        my_name=os.getenv("MY_NAME", "Founder"),
        company_name=os.getenv("MY_COMPANY_NAME", "My Company"),
        my_role=os.getenv("MY_ROLE", "Founder"),
        my_one_liner=os.getenv("MY_ONE_LINER", ""),
        auto_approve=os.getenv("AUTO_APPROVE", "false").strip().lower() in ("1", "true", "yes", "on"),
        heartbeat_hours=int(os.getenv("HEARTBEAT_HOURS", "4") or "4"),
        autonomy_level=os.getenv("AUTONOMY_LEVEL", "balanced").strip().lower(),
        voice_replies=os.getenv("VOICE_REPLIES", "true").strip().lower() in ("1", "true", "yes", "on"),
        web_ui_enabled=web_ui_enabled,
        telegram_enabled=telegram_enabled,
        dashboard_enabled=web_ui_enabled or _truthy(os.getenv("DASHBOARD_ENABLED"), default=True),
        dashboard_port=int(os.getenv("DASHBOARD_PORT", "8787") or "8787"),
        daily_llm_call_cap=int(os.getenv("DAILY_LLM_CALL_CAP", "0") or "0"),
        agent_paused=os.getenv("AGENT_PAUSED", "false").strip().lower() in ("1", "true", "yes", "on"),
        ollama_enabled=os.getenv("OLLAMA_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip(),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1").strip(),
        semantic_cache=os.getenv("SEMANTIC_CACHE", "true").strip().lower() in ("1", "true", "yes", "on"),
        cache_distance_threshold=float(os.getenv("CACHE_DISTANCE_THRESHOLD", "0.08") or "0.08"),
        tool_rag=os.getenv("TOOL_RAG", "true").strip().lower() in ("1", "true", "yes", "on"),
        tool_rag_k=int(os.getenv("TOOL_RAG_K", "16") or "16"),
        google_credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH", "./data/google_credentials.json"),
        google_token_path=os.getenv("GOOGLE_TOKEN_PATH", "./data/google_token.json"),
        x_api_key=os.getenv("X_API_KEY", ""),
        x_api_secret=os.getenv("X_API_SECRET", ""),
        x_access_token=os.getenv("X_ACCESS_TOKEN", ""),
        x_access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET", ""),
        x_bearer_token=os.getenv("X_BEARER_TOKEN", ""),
        qdrant_url=os.getenv("QDRANT_URL", "").strip().rstrip("/"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY", "").strip(),
        qdrant_collection_prefix=os.getenv("QDRANT_COLLECTION_PREFIX", "").strip(),
        github_client_id=os.getenv("GITHUB_CLIENT_ID", "").strip(),
        github_client_secret=os.getenv("GITHUB_CLIENT_SECRET", "").strip(),
        github_token_path=os.getenv("GITHUB_TOKEN_PATH", "./data/github_token.json"),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/"),
        behind_proxy=_truthy(os.getenv("BEHIND_PROXY"), default=False),
        dashboard_pin=os.getenv("DASHBOARD_PIN", "").strip(),
        flask_secret_key=os.getenv("FLASK_SECRET_KEY", "").strip() or "dev-change-me",
        github_redirect_uri=os.getenv("GITHUB_REDIRECT_URI", "").strip()
        or (
            f"{os.getenv('PUBLIC_BASE_URL', '').strip().rstrip('/')}/api/github/callback"
            if os.getenv("PUBLIC_BASE_URL", "").strip()
            else f"http://127.0.0.1:{int(os.getenv('DASHBOARD_PORT', '8787') or '8787')}/api/github/callback"
        ),
    )

config = load_config()
