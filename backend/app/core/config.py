import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./papers.db")
        self.database_echo = os.getenv("DATABASE_ECHO", "0") == "1"
        self.hf_daily_url = os.getenv(
            "HF_DAILY_URL", "https://huggingface.co/papers/date/"
        )
        self.request_timeout = float(os.getenv("REQUEST_TIMEOUT", "20"))
        self.user_agent = os.getenv(
            "REQUEST_USER_AGENT",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
        )
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.breakthrough_threshold = float(os.getenv("BREAKTHROUGH_THRESHOLD", "0.7"))
        self.tracked_institutions = {
            item.strip().lower()
            for item in os.getenv(
                "INSTITUTION_WHITELIST",
                "ai2,allen institute for ai,anthropic,openai,google deepmind,deepseek,meta ai,meta fair",
            ).split(",")
            if item.strip()
        }

        # Email/Brevo settings
        self.brevo_api_key = os.getenv("BREVO_API_KEY")
        self.email_from_address = os.getenv("EMAIL_FROM_ADDRESS", "noreply@yourdomain.com")
        self.email_from_name = os.getenv("EMAIL_FROM_NAME", "Daily Paper Insights")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8000")
        self.daily_digest_hour = int(os.getenv("DAILY_DIGEST_HOUR", "8"))  # Default: 8 AM


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()