#!/usr/bin/env python3
"""
Local Troubleshooting Hub HTTP Server & Markdown Indexing Engine.

Scans formatted Markdown subdirectories under the hub root (plus optional
extra read-only directories via --extra-dir or TROUBLE_EXTRA_DIRS), extracts
structured metadata and full-text search content, and serves a local-only
Markdown renderer.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import datetime
import hashlib
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

DEFAULT_HOST: str = "127.0.0.1"
DEFAULT_PORT: int = 8898
PRIMARY_ROOT: Path = Path(__file__).resolve().parent
MAX_MARKDOWN_BYTES: int = 2 * 1024 * 1024  # 2 MiB guard per .md file

IGNORED_DIR_NAMES: frozenset[str] = frozenset({
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
})

METADATA_FIELD_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*[-*]\s+\*\*(Date|Host|Status|Tags)\*\*\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
HEADING_PATTERN: re.Pattern[str] = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
CODE_FENCE_PATTERN: re.Pattern[str] = re.compile(r"^```")


@dataclass(frozen=True)
class SourceRoot:
    """Represents a root directory scanned for Markdown troubleshooting files."""
    key: str
    label: str
    path: Path


@dataclass(frozen=True)
class HeadingEntry:
    """Represents a section heading for Table of Contents navigation."""
    level: int
    text: str
    anchor: str


@dataclass(frozen=True)
class DocumentSummary:
    """Searchable metadata and summary record for a Markdown document."""
    id: str
    source_key: str
    source_label: str
    category: str
    rel_path: str
    filename: str
    title: str
    date: str
    host: str
    status: str
    tags: List[str]
    excerpt: str
    search_text: str
    headings: List[HeadingEntry]
    size_bytes: int
    size_formatted: str
    mtime: int
    is_template: bool

    def to_dict(self) -> Dict[str, object]:
        """Serialize summary dataclass into a JSON-compatible dictionary."""
        return asdict(self)


def format_bytes(size: int) -> str:
    """Format byte count into human-readable units."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.2f} MB"


def slugify_anchor(text: str) -> str:
    """Generate a deterministic HTML heading anchor slug."""
    cleaned = re.sub(r"`([^`]+)`", r"\1", text)
    cleaned = re.sub(r"[^\w\s-]", "", cleaned, flags=re.UNICODE).strip().lower()
    return re.sub(r"[-\s]+", "-", cleaned) or "section"


def humanize_category(raw_folder: str) -> str:
    """Convert a folder slug like 'boot-and-startup' into 'Boot & Startup'."""
    if not raw_folder or raw_folder == ".":
        return "Overview"
    words = raw_folder.replace("_", "-").split("-")
    formatted: List[str] = []
    for word in words:
        lower = word.lower()
        if lower == "and":
            formatted.append("&")
        elif lower in {"vps", "pc", "os", "ui", "api", "cli", "dns", "tls", "adb"}:
            formatted.append(lower.upper())
        else:
            formatted.append(word.capitalize())
    return " ".join(formatted)


class MarkdownMetadataParser:
    """Extracts structured troubleshooting metadata, headings, and searchable text."""

    @staticmethod
    def parse(content: str, fallback_title: str) -> Tuple[
        str, str, str, str, List[str], str, str, List[HeadingEntry]
    ]:
        """
        Parse raw Markdown into:
        (title, date, host, status, tags, excerpt, search_text, headings).
        """
        title: str = fallback_title
        date: str = ""
        host: str = ""
        status: str = ""
        tags: List[str] = []
        headings: List[HeadingEntry] = []
        excerpt_parts: List[str] = []
        plain_lines: List[str] = []

        in_code_block = False
        seen_title = False
        anchor_counts: Dict[str, int] = {}

        for raw_line in content.splitlines():
            stripped = raw_line.strip()
            if CODE_FENCE_PATTERN.match(stripped):
                in_code_block = not in_code_block
                continue

            if not in_code_block:
                heading_match = HEADING_PATTERN.match(raw_line)
                if heading_match:
                    level = len(heading_match.group(1))
                    heading_text = heading_match.group(2).strip()
                    if level == 1 and not seen_title:
                        title = heading_text
                        seen_title = True
                    else:
                        base_anchor = slugify_anchor(heading_text)
                        count = anchor_counts.get(base_anchor, 0) + 1
                        anchor_counts[base_anchor] = count
                        anchor = base_anchor if count == 1 else f"{base_anchor}-{count}"
                        headings.append(HeadingEntry(level=level, text=heading_text, anchor=anchor))
                    plain_lines.append(heading_text)
                    continue

                meta_match = METADATA_FIELD_PATTERN.match(raw_line)
                if meta_match:
                    field = meta_match.group(1).lower()
                    val = meta_match.group(2).strip()
                    if field == "date" and not date:
                        date = val
                    elif field == "host" and not host:
                        host = val
                    elif field == "status" and not status:
                        status = val
                    elif field == "tags":
                        tags.extend(t.strip().lower() for t in val.split(",") if t.strip())
                    plain_lines.append(val)
                    continue

                if stripped and not stripped.startswith(("|", "---", "<!--")) and len(excerpt_parts) < 2:
                    cleaned_prose = re.sub(r"[*_`#>\[\]]", "", stripped)
                    if cleaned_prose:
                        excerpt_parts.append(cleaned_prose)

            cleaned = re.sub(r"[*_`#>\[\]()]", " ", raw_line)
            if cleaned.strip():
                plain_lines.append(cleaned.strip())

        excerpt = " ".join(excerpt_parts)[:220].strip()
        if len(excerpt) == 220:
            excerpt = excerpt.rsplit(" ", 1)[0] + "…"
        search_text = re.sub(r"\s+", " ", " ".join(plain_lines)).lower()

        return title, date, host, status, tags, excerpt, search_text, headings


class TroubleshootingIndexService:
    """
    Safely scans configured directories for Markdown files, builds a searchable
    catalog, and serves individual documents strictly by validated ID.
    """

    def __init__(self, primary_root: Path, extra_roots: List[SourceRoot]) -> None:
        self.primary_root: Path = primary_root.resolve()
        self.roots: List[SourceRoot] = [
            SourceRoot(key="hub", label="Local Hub", path=self.primary_root),
            *extra_roots,
        ]
        self._doc_paths: Dict[str, Tuple[SourceRoot, Path]] = {}

    @staticmethod
    def _is_confined(target: Path, base_dir: Path) -> bool:
        """Verify resolved target resides strictly inside base_dir."""
        try:
            return target.resolve().is_relative_to(base_dir.resolve())
        except OSError:
            return False

    @staticmethod
    def _build_doc_id(source_key: str, rel_posix: str) -> str:
        """Create a stable, URL-safe identifier for a document."""
        digest = hashlib.sha256(f"{source_key}:{rel_posix}".encode("utf-8")).hexdigest()[:12]
        slug = re.sub(r"[^\w-]+", "-", Path(rel_posix).stem.lower()).strip("-") or "doc"
        return f"{slug[:40]}-{digest}"

    @staticmethod
    def _should_skip_path(rel_path: Path) -> bool:
        """Skip hidden directories, caches, and internal metadata dirs."""
        for part in rel_path.parts[:-1]:
            if part.startswith(".") or part in IGNORED_DIR_NAMES:
                return True
        return False

    def scan(self) -> List[DocumentSummary]:
        """Scan all configured source roots and return sorted DocumentSummary entries."""
        summaries: List[DocumentSummary] = []
        new_path_map: Dict[str, Tuple[SourceRoot, Path]] = {}

        for root in self.roots:
            resolved_root = root.path.resolve()
            if not resolved_root.is_dir():
                continue

            for md_file in sorted(resolved_root.rglob("*.md")):
                if not md_file.is_file():
                    continue
                if not self._is_confined(md_file, resolved_root):
                    continue

                rel_path = md_file.relative_to(resolved_root)
                if self._should_skip_path(rel_path):
                    continue

                try:
                    stat = md_file.stat()
                    if stat.st_size > MAX_MARKDOWN_BYTES:
                        continue
                    content = md_file.read_text(encoding="utf-8", errors="replace")
                except OSError as exc:
                    print(f"[Index] Skipping unreadable file {md_file}: {exc}", file=sys.stderr)
                    continue

                rel_posix = rel_path.as_posix()
                doc_id = self._build_doc_id(root.key, rel_posix)
                folder_part = rel_path.parent.as_posix() if rel_path.parent != Path(".") else ""
                if root.key == "hub":
                    category = humanize_category(folder_part) if folder_part else "Overview"
                else:
                    category = root.label if not folder_part else f"{root.label} / {humanize_category(folder_part)}"

                fallback_title = md_file.stem.replace("-", " ").replace("_", " ").title()
                title, date, host, status, tags, excerpt, search_text, headings = MarkdownMetadataParser.parse(
                    content, fallback_title=fallback_title
                )

                is_template = md_file.name.upper() == "TEMPLATE.MD" or "templates" in rel_path.parts
                summary = DocumentSummary(
                    id=doc_id,
                    source_key=root.key,
                    source_label=root.label,
                    category=category,
                    rel_path=rel_posix,
                    filename=md_file.name,
                    title=title,
                    date=date,
                    host=host,
                    status=status or ("Template" if is_template else "Reference"),
                    tags=tags,
                    excerpt=excerpt,
                    search_text=search_text,
                    headings=headings,
                    size_bytes=stat.st_size,
                    size_formatted=format_bytes(stat.st_size),
                    mtime=int(stat.st_mtime * 1000),
                    is_template=is_template,
                )
                summaries.append(summary)
                new_path_map[doc_id] = (root, md_file.resolve())

        summaries.sort(
            key=lambda d: (
                d.is_template,
                d.filename.upper() == "README.MD",
                -(int(d.date.replace("-", "")) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.date) else 0),
                -d.mtime,
                d.title.lower(),
            )
        )
        self._doc_paths = new_path_map
        return summaries

    def write_manifest(self, summaries: List[DocumentSummary]) -> None:
        """Atomically persist files.json manifest in primary_root."""
        manifest_path = self.primary_root / "files.json"
        payload = json.dumps([s.to_dict() for s in summaries], indent=2, ensure_ascii=False)
        with tempfile.NamedTemporaryFile("w", dir=self.primary_root, delete=False, encoding="utf-8") as tf:
            tf.write(payload)
            temp_path = Path(tf.name)
        temp_path.replace(manifest_path)

    def get_document(self, doc_id: str) -> Optional[Dict[str, object]]:
        """Load full Markdown body and metadata for an indexed document ID."""
        if doc_id not in self._doc_paths:
            self.scan()
        entry = self._doc_paths.get(doc_id)
        if entry is None:
            return None

        root, file_path = entry
        if not self._is_confined(file_path, root.path) or not file_path.is_file():
            return None

        try:
            stat = file_path.stat()
            if stat.st_size > MAX_MARKDOWN_BYTES:
                return None
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        rel_posix = file_path.relative_to(root.path.resolve()).as_posix()
        fallback_title = file_path.stem.replace("-", " ").replace("_", " ").title()
        title, date, host, status, tags, excerpt, _, headings = MarkdownMetadataParser.parse(
            content, fallback_title=fallback_title
        )

        return {
            "id": doc_id,
            "source_key": root.key,
            "source_label": root.label,
            "rel_path": rel_posix,
            "filename": file_path.name,
            "title": title,
            "date": date,
            "host": host,
            "status": status or "Reference",
            "tags": tags,
            "excerpt": excerpt,
            "headings": [asdict(h) for h in headings],
            "content": content,
            "size_formatted": format_bytes(stat.st_size),
            "mtime": int(stat.st_mtime * 1000),
        }


class TroubleshootingHTTPHandler(SimpleHTTPRequestHandler):
    """HTTP controller serving the static UI and read-only Markdown index API."""

    index_service: TroubleshootingIndexService

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(self.index_service.primary_root), **kwargs)

    def _send_json(self, status: int, payload: object) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"

        if route == "/api/status":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "online",
                    "service": "Troubleshooting Hub",
                    "roots": [
                        {"key": r.key, "label": r.label, "exists": r.path.is_dir()}
                        for r in self.index_service.roots
                    ],
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
            )
            return

        if route == "/api/docs":
            summaries = self.index_service.scan()
            self._send_json(
                HTTPStatus.OK,
                {
                    "count": len(summaries),
                    "docs": [s.to_dict() for s in summaries],
                    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
            )
            return

        if route == "/api/doc":
            query = parse_qs(parsed.query)
            doc_id = (query.get("id") or [""])[0].strip()
            if not doc_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing 'id' query parameter"})
                return
            doc = self.index_service.get_document(doc_id)
            if doc is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Document '{doc_id}' not found"})
                return
            self._send_json(HTTPStatus.OK, doc)
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/")
        if route == "/api/rescan":
            summaries = self.index_service.scan()
            self.index_service.write_manifest(summaries)
            self._send_json(HTTPStatus.OK, {"count": len(summaries), "status": "rescanned"})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Endpoint '{route}' not found"})

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {self.address_string()} - {format % args}\n"
        )


def resolve_extra_dirs(cli_extra_dirs: Optional[List[Path]]) -> List[Path]:
    """Combine CLI --extra-dir flags and TROUBLE_EXTRA_DIRS env var."""
    if cli_extra_dirs is not None:
        return cli_extra_dirs
    env_raw = os.environ.get("TROUBLE_EXTRA_DIRS", "").strip()
    if not env_raw:
        return []
    return [Path(p) for p in env_raw.split(os.pathsep) if p.strip()]


def run_server(host: str, port: int, root_dir: Path, extra_dirs: List[Path]) -> None:
    """Initialize index service, refresh manifest, and start local HTTP server."""
    extra_roots: List[SourceRoot] = []
    for idx, extra in enumerate(extra_dirs, start=1):
        resolved = extra.resolve()
        label = "External Docs" if len(extra_dirs) == 1 else f"External Docs ({humanize_category(resolved.name)})"
        key = f"extra_{idx}"
        extra_roots.append(SourceRoot(key=key, label=label, path=resolved))

    index_service = TroubleshootingIndexService(primary_root=root_dir, extra_roots=extra_roots)
    summaries = index_service.scan()
    index_service.write_manifest(summaries)

    TroubleshootingHTTPHandler.index_service = index_service
    httpd = ThreadingHTTPServer((host, port), TroubleshootingHTTPHandler)

    print(f"🛠️  Troubleshooting Hub active on http://{host}:{port}/")
    print(f"📁 Primary root: {root_dir.resolve()} ({len(summaries)} indexed docs)")
    for extra in extra_roots:
        print(f"📚 Extra root:   {extra.path} ({'present' if extra.path.is_dir() else 'missing'})")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Troubleshooting Hub...")
    finally:
        httpd.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Troubleshooting Hub HTTP Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Bind address (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Bind port (default: {DEFAULT_PORT})")
    parser.add_argument("--dir", type=Path, default=PRIMARY_ROOT, help="Primary troubleshooting directory")
    parser.add_argument(
        "--extra-dir",
        type=Path,
        action="append",
        default=None,
        help="Additional Markdown directory to index (read-only)",
    )
    args = parser.parse_args()

    extra_dirs = resolve_extra_dirs(args.extra_dir)
    run_server(host=args.host, port=args.port, root_dir=args.dir, extra_dirs=extra_dirs)


if __name__ == "__main__":
    main()
