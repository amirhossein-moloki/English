import hashlib
import mimetypes
from pathlib import Path
from typing import Tuple, Optional, List


class AudioValidator:
    ALLOWED_MIME_TYPES = {
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/ogg",
        "audio/aac",
        "audio/m4a",
        "audio/mp4",
        "application/octet-stream",  # Edge TTS / CDN streams sometimes return raw octet stream
    }

    ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".aac", ".m4a"}

    @classmethod
    def validate_bytes(
        cls,
        content: bytes,
        filename_or_url: str,
        content_type: Optional[str] = None,
        max_size_bytes: int = 5242880
    ) -> Tuple[bool, str, str, str]:
        """Validates raw audio bytes.
        Returns: (is_valid, error_reason_or_ok, mime_type, sha256_hash)
        """
        if not content or len(content) == 0:
            return False, "Audio content is empty (0 bytes)", "", ""

        if len(content) > max_size_bytes:
            return False, f"Audio file exceeds maximum size limit ({len(content)} > {max_size_bytes} bytes)", "", ""

        # Check for obvious HTML response (e.g. 404/500 error page returned as 200)
        snippet = content[:100].lower()
        if b"<!doctype html" in snippet or b"<html" in snippet or b"<?xml" in snippet:
            return False, "Received HTML/XML webpage instead of valid audio binary", "", ""

        # Determine MIME type
        mime = (content_type or "").split(";")[0].strip().lower()
        if not mime or mime == "application/octet-stream":
            guessed_mime, _ = mimetypes.guess_type(filename_or_url)
            if guessed_mime:
                mime = guessed_mime
            else:
                mime = "audio/mpeg"  # Default fallback

        if mime not in cls.ALLOWED_MIME_TYPES and not mime.startswith("audio/"):
            return False, f"Invalid Content-Type/MIME type: {mime}", "", ""

        # Compute SHA256
        sha256 = hashlib.sha256(content).hexdigest()

        return True, "OK", mime, sha256
