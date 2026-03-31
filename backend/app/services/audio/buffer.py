from __future__ import annotations


class AudioBuffer:
    def __init__(self, *, max_bytes: int) -> None:
        self._max_bytes = max_bytes
        self._chunks: list[bytes] = []
        self._size = 0

    def append(self, chunk: bytes) -> None:
        new_size = self._size + len(chunk)
        if new_size > self._max_bytes:
            raise ValueError("Audio buffer limit exceeded")
        self._chunks.append(chunk)
        self._size = new_size

    def flush(self) -> bytes:
        data = b"".join(self._chunks)
        self.reset()
        return data

    def reset(self) -> None:
        self._chunks.clear()
        self._size = 0

    @property
    def size(self) -> int:
        return self._size
