"""Service for audio transcription via faster-whisper.

The model is loaded on-demand by the worker and passed into transcribe_audio().
This avoids keeping the large model in memory during idle periods.

Design tradeoff: Loading the model takes a few seconds per wake cycle, but
eliminates persistent CPU/RAM usage when idle — worthwhile for a personal tool.
"""

import logging

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


def load_model(model_size: str = "base") -> WhisperModel:
    """Load and return a WhisperModel instance.

    Caller is responsible for lifecycle (delete when done to free memory).
    """
    logger.info("Loading Whisper model: %s", model_size)
    return WhisperModel(model_size, device="cpu")


def transcribe_audio(model: WhisperModel, audio_path: str) -> str:
    """Transcribe an audio/video file and return the full transcript text.

    Pipeline step 2: Takes a loaded model and file path, returns plain text.
    """
    logger.info("Transcribing: %s", audio_path)
    segments, _info = model.transcribe(audio_path)
    transcript = " ".join(segment.text.strip() for segment in segments)
    logger.info("Transcription complete (%d chars)", len(transcript))
    return transcript
