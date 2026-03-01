# stt.py
from RealtimeSTT import AudioToTextRecorder


class SpeechToText:
    def __init__(self, model: str, language: str):
        self.recorder = AudioToTextRecorder(
            model=model,
            language=language,
            spinner=False,
            silero_deactivity_detection=False,  # avoids Silero download issues
            webrtc_sensitivity=3,
            post_speech_silence_duration=0.4,
            min_length_of_recording=0.4,
            pre_recording_buffer_duration=0.6,
            sample_rate=16000,
        )

    def listen_text(self) -> str:
        return self.recorder.text() or ""

    def shutdown(self):
        self.recorder.shutdown()
