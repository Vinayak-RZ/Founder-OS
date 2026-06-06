"""Voice transcription for inbound Telegram voice notes.

Two engines, tried in order:
  1. faster-whisper — fully local, offline, free. Preferred if installed.
     Setup:  pip install faster-whisper
  2. OpenAI Whisper API (whisper-1) — used as a fallback when faster-whisper
     isn't installed but an OpenAI key is configured. Accepts Telegram's .ogg
     directly; ~ $0.006/min.

So as long as either faster-whisper is installed OR OPENAI_API_KEY is set, the
founder can talk to the agent instead of typing.
"""
import logging

logger = logging.getLogger(__name__)

_model = None
_MODEL_SIZE = "base"  # good speed/quality tradeoff on CPU


def _whisper_installed() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


def _openai_available() -> bool:
    try:
        from config import config
        return bool(config.openai_api_key)
    except Exception:
        return False


def available() -> bool:
    return _whisper_installed() or _openai_available()


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def _transcribe_local(path: str) -> str:
    model = _get_model()
    segments, _info = model.transcribe(path, beam_size=1)
    return " ".join(seg.text.strip() for seg in segments).strip()


def _transcribe_openai(path: str) -> str:
    from openai import OpenAI
    from config import config
    client = OpenAI(api_key=config.openai_api_key)
    with open(path, "rb") as f:
        resp = client.audio.transcriptions.create(model="whisper-1", file=f)
    return (resp.text or "").strip()


def transcribe_file(path: str) -> str:
    """Transcribe an audio file to text. Returns '' if no engine is available/all fail."""
    if _whisper_installed():
        try:
            text = _transcribe_local(path)
            if text:
                return text
        except Exception as e:
            logger.error(f"[transcribe] faster-whisper failed, falling back: {e}")
    if _openai_available():
        try:
            return _transcribe_openai(path)
        except Exception as e:
            logger.error(f"[transcribe] OpenAI whisper failed: {e}")
    return ""
