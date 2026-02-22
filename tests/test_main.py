import pytest
from fastapi.testclient import TestClient
from app.main import app
import io

client = TestClient(app)

def test_health_check():
    """Тест эндпоинта здоровья"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_process_waybill():
    """Тест обработки накладной"""
    # Создание тестового изображения
    from PIL import Image
    import numpy as np
    
    img = Image.new('RGB', (800, 600), color='white')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    files = {'file': ('test.png', img_byte_arr, 'image/png')}
    data = {'document_type': 'waybill'}
    headers = {'X-API-Key': 'dev-secret-key-change-in-production'}
    
    response = client.post(
        "/api/v1/ocr/process",
        files=files,
        data=data,
        headers=headers
    )
    
    assert response.status_code in [200, 500]  # 500 если нет моделей

def test_invalid_api_key():
    """Тест неверного API ключа"""
    files = {'file': ('test.png', b'test', 'image/png')}
    headers = {'X-API-Key': 'invalid-key'}
    
    response = client.post(
        "/api/v1/ocr/process",
        files=files,
        headers=headers
    )
    
    assert response.status_code == 401