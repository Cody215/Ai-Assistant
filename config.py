# config.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class AppConfig:
    # API keys
    gemini_api_key: str
    elevenlabs_api_key: str

    # LLM
    gemini_model: str = "gemini-2.5-flash"
    system_instruction: str = (
        "You are Jarvis, a sharp and reliable desktop voice assistant. "
        "You have a calm, confident tone — helpful without being overly cheerful. "
        "Keep spoken responses concise and natural (under 40 words when possible). "
        "When you use a tool, do not narrate it — just act. "
        "For simple questions, answer directly without reaching for a tool. "
        "Never mention JSON, tools, or internal workings in your replies."
    )

    # Speech-to-text
    stt_model: str = "base.en"
    stt_language: str = "en"

    # Text-to-speech (ElevenLabs)
    eleven_voice_id: str = "IKne3meq5aSn9XLyUdCD"
    eleven_model_id: str = "eleven_flash_v2_5"
    eleven_output_format: str = "mp3_44100_128"

    # Push-to-talk
    ptt_enabled: bool = True
    ptt_key: str = "F9"

    # Timezone default
    default_timezone: str = "Australia/Sydney"

    # mpv path (for low-latency audio playback)
    mpv_path: str = "mpv.exe"


def load_config() -> AppConfig:
    load_dotenv()

    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    eleven_api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()

    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env")
    if not eleven_api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in .env")

    return AppConfig(
        gemini_api_key=gemini_api_key,
        elevenlabs_api_key=eleven_api_key,
    )
