from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.core.config import settings
from app.services.audio.buffer import AudioBuffer


@dataclass
class VoiceSession:
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    audio_buffer: AudioBuffer = field(
        default_factory=lambda: AudioBuffer(max_bytes=settings.voice_input_buffer_max_bytes)
    )

    def reset_turn(self) -> None:
        self.audio_buffer.reset()
