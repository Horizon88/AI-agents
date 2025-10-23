"""Document collection utilities for the e-discovery platform."""

from __future__ import annotations

import os
import shutil
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class CollectedDocument:
    """Represents a collected document stored locally."""

    source: str
    local_path: Path


class DocumentCollector:
    """Collects documents from local paths or downloadable URLs."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def collect(self, sources: Iterable[str]) -> List[CollectedDocument]:
        """Collects documents from the given sources.

        Args:
            sources: Iterable of file paths or URLs.

        Returns:
            List of CollectedDocument items representing copied/downloaded files.
        """

        collected: List[CollectedDocument] = []
        for source in sources:
            source = source.strip()
            if not source:
                continue
            parsed = urllib.parse.urlparse(source)
            if parsed.scheme in {"http", "https"}:
                document = self._download_file(source)
            else:
                document = self._copy_local_file(Path(source))
            if document:
                collected.append(document)
        return collected

    def _download_file(self, url: str) -> Optional[CollectedDocument]:
        """Downloads a file from a URL to the storage directory."""
        filename = Path(urllib.parse.urlparse(url).path).name or "downloaded_document"
        tmp_fd, tmp_path = tempfile.mkstemp()
        os.close(tmp_fd)
        try:
            with urllib.request.urlopen(url) as response, open(tmp_path, "wb") as tmp_file:
                shutil.copyfileobj(response, tmp_file)
            destination = self.storage_dir / filename
            shutil.move(tmp_path, destination)
            return CollectedDocument(source=url, local_path=destination)
        except Exception as exc:  # pragma: no cover - logging or UI feedback handles errors
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            print(f"Failed to download {url}: {exc}")
            return None

    def _copy_local_file(self, path: Path) -> Optional[CollectedDocument]:
        """Copies a local file to the storage directory."""
        if not path.exists():
            print(f"File not found: {path}")
            return None
        destination = self.storage_dir / path.name
        try:
            shutil.copy(path, destination)
            return CollectedDocument(source=str(path), local_path=destination)
        except Exception as exc:  # pragma: no cover - logging or UI feedback handles errors
            print(f"Failed to copy {path}: {exc}")
            return None
