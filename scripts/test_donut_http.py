#!/usr/bin/env python3
"""
Скрипт для тестирования Donut API через HTTP запросы.

Требует запущенного сервера:
  uvicorn app.main:app --reload

Использование:
  python scripts/test_donut_http.py --path static/image.jpg --doc-type waybill --url http://localhost:8000
  python scripts/test_donut_http.py --path document.pdf --doc-type invoice
"""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Optional

import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_donut_http_extract(
    file_path: str | Path,
    document_type: str = "invoice",
    api_url: str = "http://localhost:8000",
    timeout: int = 60,
) -> dict:
    """
    Тестирует Donut extraction через HTTP API.
    
    Parameters
    ----------
    file_path : str | Path
        Путь к файлу документа
    document_type : str
        Тип документа (waybill, invoice, act, upd)
    api_url : str
        Base URL API сервера
    timeout : int
        Timeout для запроса (в секундах)
    """
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    
    logger.info("=" * 60)
    logger.info("Donut HTTP API Test")
    logger.info("=" * 60)
    
    try:
        # 1. Проверяем доступность сервера
        logger.info(f"\n1. Проверяем доступность сервера ({api_url})...")
        
        try:
            health_response = requests.get(f"{api_url}/health", timeout=5)
            if health_response.status_code == 200:
                logger.info(f"   ✓ Сервер доступен: {health_response.json()}")
            else:
                logger.warning(f"   ⚠ Сервер вернул статус {health_response.status_code}")
        except requests.ConnectionError:
            logger.error(f"   ✗ Не удалось подключиться к {api_url}")
            logger.error(f"   Убедитесь, что сервер запущен: uvicorn app.main:app --reload")
            raise
        
        # 2. Получаем информацию о модели
        logger.info(f"\n2. Получаем информацию о Donut модели...")
        
        try:
            info_response = requests.get(
                f"{api_url}/api/v1/donut/info",
                timeout=timeout,
            )
            
            if info_response.status_code == 200:
                info_data = info_response.json()
                logger.info(f"   ✓ Модель: {info_data['model']}")
                logger.info(f"   ✓ Device: {info_data['device']}")
                logger.info(f"   ✓ Max file size: {info_data['max_file_size_mb']} MB")
            else:
                logger.warning(f"   ⚠ Статус {info_response.status_code}: {info_response.text}")
        except Exception as e:
            logger.warning(f"   ⚠ Не удалось получить информацию: {e}")
        
        # 3. Загружаем и отправляем файл
        logger.info(f"\n3. Отправляем документ на обработку...")
        logger.info(f"   Файл: {file_path}")
        logger.info(f"   Тип: {document_type}")
        
        # Определяем MIME type
        suffix = file_path.suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf',
        }
        mime_type = mime_types.get(suffix, 'image/jpeg')
        
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, mime_type)}
            params = {'document_type': document_type}
            
            start_time = time.time()
            
            response = requests.post(
                f"{api_url}/api/v1/donut/extract",
                files=files,
                params=params,
                timeout=timeout,
            )
            
            elapsed_time = time.time() - start_time
        
        # 4. Обрабатываем результат
        logger.info(f"   ✓ Ответ получен за {elapsed_time:.2f}s")
        logger.info(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            logger.info(f"\n4. Результаты обработки:")
            logger.info(f"   Status: {result['status']}")
            logger.info(f"   Confidence: {result['confidence']:.2%}")
            logger.info(f"   Processing time: {result['processing_time_ms']}ms")
            
            # Выводим извлеченные данные
            logger.info(f"\n5. Извлеченные данные:")
            extracted = result.get('extracted_data', {})
            
            if isinstance(extracted, dict):
                for key, value in extracted.items():
                    if isinstance(value, (dict, list)):
                        value_str = str(value)[:80]
                    else:
                        value_str = str(value)
                    logger.info(f"   {key}: {value_str}")
            else:
                logger.info(f"   {extracted}")
            
            # Сохраняем полный результат
            logger.info(f"\n6. Сохраняю полный результат в 'donut_result.json'...")
            with open('donut_result.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"   ✓ Результат сохранен")
            
            return {
                "status": "success",
                "http_status": response.status_code,
                "extraction_time": elapsed_time,
                "result": result,
            }
        
        else:
            logger.error(f"   ✗ Ошибка: {response.status_code}")
            logger.error(f"   {response.text}")
            
            return {
                "status": "error",
                "http_status": response.status_code,
                "error": response.text,
            }
        
    except Exception as e:
        logger.error(f"✗ Критическая ошибка: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }
    
    finally:
        logger.info("\n" + "=" * 60)


def test_donut_parse_json(
    raw_output: str,
    document_type: str = "invoice",
    api_url: str = "http://localhost:8000",
) -> dict:
    """
    Тестирует парсинг JSON результата Donut через API.
    """
    
    logger.info("\n" + "=" * 60)
    logger.info("Donut JSON Parse Test")
    logger.info("=" * 60)
    
    try:
        logger.info(f"\n1. Отправляю JSON на парсинг...")
        
        response = requests.post(
            f"{api_url}/api/v1/donut/parse-json",
            params={
                'raw_output': raw_output,
                'document_type': document_type,
            },
            timeout=30,
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"   ✓ Парсинг успешен")
            logger.info(f"   Данные: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            return {
                "status": "success",
                "result": result,
            }
        else:
            logger.error(f"   ✗ Ошибка: {response.status_code}")
            logger.error(f"   {response.text}")
            
            return {
                "status": "error",
                "error": response.text,
            }
    
    except Exception as e:
        logger.error(f"✗ Ошибка: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }
    
    finally:
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Тест Donut HTTP API",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Путь к файлу документа (JPEG, PNG, PDF)",
    )
    
    parser.add_argument(
        "--doc-type",
        type=str,
        default="invoice",
        choices=["waybill", "invoice", "act", "upd"],
        help="Тип документа",
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Base URL API сервера",
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout для HTTP запроса (в секундах)",
    )
    
    args = parser.parse_args()
    
    # Запускаем тест
    result = test_donut_http_extract(
        file_path=args.path,
        document_type=args.doc_type,
        api_url=args.url,
        timeout=args.timeout,
    )
    
    # Выводим результат
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    print(json.dumps(
        {k: v for k, v in result.items() if k != 'result'},
        indent=2,
        ensure_ascii=False
    ))


if __name__ == "__main__":
    main()
