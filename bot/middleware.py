from config import config

def is_authorized(user_id: int) -> bool:
    # PUBLIC_ACCESS opens the bot to ANY Telegram user. Off by default so the
    # bot only answers its owner. See README §security before enabling.
    if config.public_access:
        return True
    return user_id == config.my_telegram_user_id
