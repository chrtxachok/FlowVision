#!/usr/bin/env python3
"""
Локальный smoke-test OCR.

Запускать из корня проекта:
  python scripts/test_ocr.py --path static/image.jpg --doc-type waybill
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path


# Добавляем корень репозитория в sys.path, чтобы корректно импортировался пакет app
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".pdf":
        return "application/pdf"
    return "application/octet-stream"


async def _run(path: Path, mime: str, doc_type: str) -> int:
    from app.services.ocr_service import OCRService

    service = OCRService()
    file_bytes = path.read_bytes()
    resp = await service.process_document(
        file_bytes=file_bytes,
        file_type=mime,
        document_type=doc_type,
    )

    payload = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, default="static/image.jpg", help="Путь к изображению или PDF")
    parser.add_argument("--mime", type=str, default="", help="MIME-тип (если не указан — определится по расширению)")
    parser.add_argument("--doc-type", type=str, default="waybill", help="Тип документа (waybill/invoice/...)")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    mime = args.mime.strip() or _guess_mime(path)
    if mime not in {"image/jpeg", "image/png", "application/pdf"}:
        raise SystemExit(f"Unsupported mime '{mime}'. Use image/jpeg, image/png, application/pdf")

    return asyncio.run(_run(path=path, mime=mime, doc_type=args.doc_type))


if __name__ == "__main__":
    raise SystemExit(main())
