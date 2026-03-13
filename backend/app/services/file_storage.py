"""VULKRAN OS — File storage service.

Handles file uploads, downloads, and organization on the VPS filesystem.
Security: magic bytes validation, filename sanitization, size limits.
"""

import hashlib
import mimetypes
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings

settings = get_settings()

# Max upload size per file (10 MB default)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed MIME types and their magic bytes signatures
ALLOWED_TYPES = {
    # Images
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],  # RIFF....WEBP
    "image/svg+xml": [b"<?xml", b"<svg"],
    # Documents
    "application/pdf": [b"%PDF"],
    # Video
    "video/mp4": [b"\x00\x00\x00", b"ftyp"],
    # Audio
    "audio/mpeg": [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"ID3"],
    # Archives (for templates)
    "application/zip": [b"PK\x03\x04"],
}

# Dangerous extensions (never allow)
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js",
    ".msi", ".dll", ".so", ".py", ".php", ".rb", ".pl",
}


def _sanitize_filename(filename: str) -> str:
    """Remove path traversal attempts and dangerous characters."""
    # Strip any directory components
    name = Path(filename).name
    # Remove non-ASCII and special chars (keep alphanumeric, dots, hyphens, underscores)
    name = re.sub(r"[^\w.\-]", "_", name)
    # Collapse multiple underscores/dots
    name = re.sub(r"_{2,}", "_", name)
    name = re.sub(r"\.{2,}", ".", name)
    # Limit length
    if len(name) > 200:
        stem, ext = name.rsplit(".", 1) if "." in name else (name, "")
        name = f"{stem[:190]}.{ext}" if ext else stem[:200]
    return name or "unnamed"


def _validate_magic_bytes(content: bytes, claimed_mime: str) -> bool:
    """Check file's magic bytes against claimed MIME type."""
    if claimed_mime not in ALLOWED_TYPES:
        return False
    signatures = ALLOWED_TYPES[claimed_mime]
    return any(content[:len(sig)] == sig for sig in signatures)


def _get_client_dir(client_slug: str) -> Path:
    """Get the base directory for a client's files."""
    base = Path(settings.data_dir) / "clients" / client_slug
    base.mkdir(parents=True, exist_ok=True)
    return base


class FileStorageError(Exception):
    pass


class FileStorage:
    """Manages file operations for client assets."""

    @staticmethod
    def upload(
        client_slug: str,
        category: str,  # brand | content | invoices | templates
        filename: str,
        content: bytes,
        mime_type: str | None = None,
    ) -> dict:
        """Upload a file to a client's storage.

        Returns metadata dict with path, url, size, etc.
        """
        # Size check
        if len(content) > MAX_FILE_SIZE:
            raise FileStorageError(
                f"File too large: {len(content)} bytes (max {MAX_FILE_SIZE})"
            )

        # Sanitize filename
        safe_name = _sanitize_filename(filename)

        # Check extension
        ext = Path(safe_name).suffix.lower()
        if ext in BLOCKED_EXTENSIONS:
            raise FileStorageError(f"File type not allowed: {ext}")

        # Determine MIME type
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(safe_name)
        if not mime_type:
            raise FileStorageError("Cannot determine file type")

        # Validate magic bytes (skip for SVG which is text)
        if mime_type != "image/svg+xml" and not _validate_magic_bytes(content, mime_type):
            raise FileStorageError(
                f"File content does not match claimed type: {mime_type}"
            )

        # Build path: /data/clients/{slug}/{category}/{date}/{unique_name}
        date_prefix = datetime.now(timezone.utc).strftime("%Y-%m")
        unique_prefix = uuid.uuid4().hex[:8]
        final_name = f"{unique_prefix}_{safe_name}"

        client_dir = _get_client_dir(client_slug)
        target_dir = client_dir / category / date_prefix
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / final_name

        # Write file
        target_path.write_bytes(content)

        # Compute hash for dedup/integrity
        file_hash = hashlib.sha256(content).hexdigest()[:16]

        # Relative path from data_dir (for URL generation)
        rel_path = target_path.relative_to(Path(settings.data_dir))

        return {
            "path": str(target_path),
            "relative_path": str(rel_path),
            "url": f"/files/{rel_path}",
            "filename": final_name,
            "original_filename": filename,
            "mime_type": mime_type,
            "size": len(content),
            "hash": file_hash,
        }

    @staticmethod
    def get_file(relative_path: str) -> tuple[Path, str] | None:
        """Get a file by its relative path. Returns (full_path, mime_type) or None."""
        # Prevent path traversal
        clean = Path(relative_path)
        if ".." in clean.parts:
            return None

        full_path = Path(settings.data_dir) / clean
        if not full_path.exists() or not full_path.is_file():
            return None

        # Verify it's within data_dir
        try:
            full_path.resolve().relative_to(Path(settings.data_dir).resolve())
        except ValueError:
            return None

        mime_type, _ = mimetypes.guess_type(str(full_path))
        return full_path, mime_type or "application/octet-stream"

    @staticmethod
    def list_files(client_slug: str, category: str = "") -> list[dict]:
        """List files for a client, optionally filtered by category."""
        client_dir = _get_client_dir(client_slug)
        search_dir = client_dir / category if category else client_dir

        if not search_dir.exists():
            return []

        files = []
        for path in sorted(search_dir.rglob("*")):
            if path.is_file():
                rel = path.relative_to(Path(settings.data_dir))
                mime, _ = mimetypes.guess_type(str(path))
                files.append({
                    "path": str(rel),
                    "url": f"/files/{rel}",
                    "filename": path.name,
                    "mime_type": mime or "application/octet-stream",
                    "size": path.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        path.stat().st_mtime, tz=timezone.utc
                    ).isoformat(),
                })
        return files

    @staticmethod
    def delete_file(relative_path: str) -> bool:
        """Delete a file by relative path. Returns True if deleted."""
        clean = Path(relative_path)
        if ".." in clean.parts:
            return False

        full_path = Path(settings.data_dir) / clean
        try:
            full_path.resolve().relative_to(Path(settings.data_dir).resolve())
        except ValueError:
            return False

        if full_path.exists() and full_path.is_file():
            full_path.unlink()
            return True
        return False

    @staticmethod
    def ensure_client_structure(client_slug: str) -> dict:
        """Create the standard directory structure for a new client."""
        client_dir = _get_client_dir(client_slug)
        dirs = ["brand", "templates/static", "templates/video", "content", "invoices"]
        created = []
        for d in dirs:
            path = client_dir / d
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path.relative_to(Path(settings.data_dir))))
        return {"client_slug": client_slug, "directories": created}
