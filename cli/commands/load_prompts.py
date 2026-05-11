"""Load and index markdown files from a directory as prompt library documents."""

import argparse
import json
import os
import re
from pathlib import Path

import httpx
import yaml

from server.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_API_URL = "http://localhost:8001"


def extract_frontmatter(content: str) -> tuple[dict, str]:
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1))
            if isinstance(frontmatter, dict):
                return frontmatter, match.group(2)
        except yaml.YAMLError:
            pass
    return {}, content


def scan_markdown_files(directory: str) -> list[dict]:
    docs = []
    root = Path(directory).resolve()

    for path in root.rglob("*.md"):
        try:
            content = path.read_text(encoding="utf-8")
            if not content.strip():
                continue

            frontmatter, body = extract_frontmatter(content)
            rel_path = path.relative_to(root)
            prompt_id = str(rel_path.with_suffix("")).replace(os.sep, "/")

            doc = {
                "prompt_id": prompt_id,
                "text": body.strip(),
                "title": frontmatter.get("title")
                or path.stem.replace("-", " ").replace("_", " ").title(),
                "description": frontmatter.get("description"),
                "tags": frontmatter.get("tags", []),
                "file_path": str(rel_path),
                "metadata": {
                    "frontmatter": frontmatter,
                    "file_name": path.name,
                    "file_size": path.stat().st_size,
                },
            }
            docs.append(doc)
            logger.info(f"Scanned: {rel_path} -> prompt_id={prompt_id}")
        except Exception as e:
            logger.warning(f"Failed to read {path}: {e}")

    return docs


def index_documents(docs: list[dict], library_id: str, api_url: str) -> dict:
    url = f"{api_url}/prompts/index"
    payload = {
        "library_id": library_id,
        "documents": docs,
    }
    with httpx.Client() as client:
        response = client.post(url, json=payload, timeout=300.0)
        response.raise_for_status()
        data: dict = response.json()
        return data


def main():
    parser = argparse.ArgumentParser(description="Index markdown files as prompt library")
    parser.add_argument("directory", help="Directory to scan for markdown files")
    parser.add_argument("--library-id", default="dotfiles", help="Library identifier")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="RAG Params Finder API URL")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, do not index")

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        logger.error(f"Directory not found: {args.directory}")
        return 1

    logger.info(f"Scanning {args.directory} for markdown files...")
    docs = scan_markdown_files(args.directory)
    logger.info(f"Found {len(docs)} markdown files")

    if not docs:
        logger.warning("No markdown files found")
        return 0

    if args.dry_run:
        for doc in docs:
            print(f"  {doc['prompt_id']}: {doc['title']}")
        return 0

    logger.info(f"Indexing {len(docs)} documents into library={args.library_id}...")
    try:
        result = index_documents(docs, args.library_id, args.api_url)
        logger.info(f"Indexed: {result['documents_indexed']} documents")
        print(json.dumps(result, indent=2))
        return 0
    except httpx.HTTPError as e:
        logger.error(f"Indexing failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
