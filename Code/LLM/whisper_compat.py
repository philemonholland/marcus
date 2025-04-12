# Module pour rendre le code Whisper déjà codé compatible avec Faster-Whisper avec le minimum de modifications.
# Ce module est conçu pour être utilisé avec le code existant qui utilise la bibliothèque openai-whisper.
# whisper_compat.py
from faster_whisper import WhisperModel as FasterWhisperModel

class WhisperModelCompat:
    def __init__(self, model_name, device="cpu", compute_type="float32", **kwargs):
        """
        Initialize the faster-whisper model.
        """
        self.model = FasterWhisperModel(model_name, device=device, compute_type=compute_type, **kwargs)

    def transcribe(self, audio, **kwargs):
        """
        Mimics openai-whisper’s transcribe() API.
        Returns a dictionary with transcription details.
        """
        segments, info = self.model.transcribe(audio, **kwargs)
        segments = list(segments)  # Convert generator to list if necessary.
        full_text = " ".join(segment.text for segment in segments)
        return {
            "text": full_text,
            "segments": segments,
            "language": getattr(info, "language", None),
            "language_probability": getattr(info, "language_probability", None),
        }

def load_model(model_name, device="cpu", compute_type="float32", **kwargs):
    """
    This function mirrors openai-whisper's load_model.
    """
    return WhisperModelCompat(model_name, device=device, compute_type=compute_type, **kwargs)

# Only for testing the module standalone.
if __name__ == '__main__':
    # Call the function directly, without the "whisper" prefix.
    model = load_model("base", device="cuda", compute_type="float16")
    print("Model loaded:", model)
