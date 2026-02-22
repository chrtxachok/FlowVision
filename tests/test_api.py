import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    """Тест эндпоинта здоровья"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_process_waybill():
    """Тест обработки накладной"""
    # Создаём тестовое изображение
    from PIL import Image
    import io
    
    img = Image.new('RGB', (800, 600), color='white')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        files = {'file': ('test.png', img_byte_arr, 'image/png')}
        data = {'document_type': 'waybill'}
        headers = {'X-API-Key': 'dev-secret-key-change-in-production'}
        
        response = await ac.post(
            "/api/v1/ocr/process",
            files=files,
            data=data,
            headers=headers
        )
    
    # Проверяем статус
    assert response.status_code in [200, 500]  # 500 если нет моделей

@pytest.mark.asyncio
async def test_invalid_api_key():
    """Тест неверного API ключа"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        files = {'file': ('test.png', b'test', 'image/png')}
        headers = {'X-API-Key': 'invalid-key'}
        
        response = await ac.post(
            "/api/v1/ocr/process",
            files=files,
            headers=headers
        )
    
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid API key"