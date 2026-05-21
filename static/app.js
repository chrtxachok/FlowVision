// Элементы DOM
const form = document.getElementById('uploadForm');
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const submitBtn = document.getElementById('submitBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const loadingText = document.getElementById('loadingText');
const progressFill = document.getElementById('progressFill');
const resultsSection = document.getElementById('resultsSection');
const errorBox = document.getElementById('errorBox');
const errorMessage = document.getElementById('errorMessage');
const statusBox = document.getElementById('statusBox');
const statusIcon = document.getElementById('statusIcon');
const statusText = document.getElementById('statusText');
const processingTime = document.getElementById('processingTime');
const extractedData = document.getElementById('extractedData');
const rawText = document.getElementById('rawText');
const jsonResult = document.getElementById('jsonResult');
const toggleJsonBtn = document.getElementById('toggleJsonBtn');
const downloadJsonBtn = document.getElementById('downloadJsonBtn');
const newDocumentBtn = document.getElementById('newDocumentBtn');

let currentJsonData = null;
let selectedFile = null;

// Обработчики Drag-and-drop
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

// Обработка выбора файла
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

function handleFileSelect(file) {
    // Валидация типа файла
    const validTypes = ['image/jpeg', 'image/png', 'application/pdf'];
    if (!validTypes.includes(file.type)) {
        showError('Неподдерживаемый формат файла. Используйте JPG, PNG или PDF');
        return;
    }

    // Валидация размера (10 МБ)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        showError(`Файл слишком большой (макс. 10 МБ). Текущий размер: ${(file.size / 1024 / 1024).toFixed(2)} МБ`);
        return;
    }

    selectedFile = file;
    
    // Показываем информацию о файле
    fileName.textContent = file.name;
    fileSize.textContent = `${(file.size / 1024).toFixed(1)} КБ`;
    fileInfo.classList.remove('hidden');
    
    // Очищаем предыдущие результаты
    hideResults();
    hideError();
}

// Отправка формы
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!selectedFile) {
        showError('Пожалуйста, выберите файл');
        return;
    }
    
    await processDocument();
});

async function processDocument() {
    const documentType = document.getElementById('documentType').value;
    const apiKey = document.getElementById('apiKey').value;
    
    // Создаём FormData
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('document_type', documentType);
    formData.append('api_key', apiKey);
    
    // Показываем загрузку
    showLoading();
    submitBtn.disabled = true;
    hideError();
    hideResults();
    
    try {
        const startTime = Date.now();
        
        // Отправляем на сервер
        const response = await fetch('/api/v1/ocr/process', {
            method: 'POST',
            body: formData,
            timeout: 120000 // 2 минуты таймаут
        });
        
        const endTime = Date.now();
        const processingTimeMs = endTime - startTime;
        
        // Обработка ответа
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Ошибка сервера (${response.status})`);
        }
        
        const data = await response.json();
        currentJsonData = data;
        
        // Показываем результаты
        hideLoading();
        displayResults(data, processingTimeMs);
        
    } catch (error) {
        hideLoading();
        console.error('Ошибка:', error);
        showError(error.message || 'Неизвестная ошибка при обработке документа');
    } finally {
        submitBtn.disabled = false;
    }
}

function displayResults(data, processingTimeMs) {
    // Обновляем статус
    if (data.status === 'success') {
        statusIcon.textContent = '✓';
        statusIcon.style.color = '#10b981';
        statusText.textContent = 'Успешно обработано';
    } else {
        statusIcon.textContent = '⚠️';
        statusIcon.style.color = '#f59e0b';
        statusText.textContent = 'Обработано с предупреждениями';
    }
    
    processingTime.textContent = `⏱️ ${(processingTimeMs / 1000).toFixed(2)}s`;
    
    // Показываем извлеченные данные
    displayExtractedData(data.extracted_data);
    
    // Показываем сырой текст
    rawText.textContent = data.raw_text || '(нет текста)';
    
    // Показываем JSON
    jsonResult.textContent = JSON.stringify(data, null, 2);
    
    // Показываем секцию результатов
    resultsSection.classList.remove('hidden');
    
    // Скроллим к результатам
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }, 100);
}

function displayExtractedData(data) {
    extractedData.innerHTML = '';
    
    if (!data || Object.keys(data).length === 0) {
        extractedData.innerHTML = '<div class="data-item">Нет извлеченных данных</div>';
        return;
    }
    
    // Плоское отображение данных
    const flattenData = (obj, prefix = '') => {
        for (const [key, value] of Object.entries(obj)) {
            if (value === null || value === undefined) {
                const item = document.createElement('div');
                item.className = 'data-item null';
                item.innerHTML = `<strong>${key}</strong><span>(не найдено)</span>`;
                extractedData.appendChild(item);
            } else if (typeof value === 'object') {
                if (value.value !== undefined) {
                    // Структура с confidence
                    const item = document.createElement('div');
                    item.className = 'data-item';
                    const confidence = value.confidence ? ` (${(value.confidence * 100).toFixed(0)}%)` : '';
                    item.innerHTML = `<strong>${key}</strong><span>${value.value || '(нет значения)'}${confidence}</span>`;
                    extractedData.appendChild(item);
                } else {
                    // Вложенный объект
                    flattenData(value, key);
                }
            } else {
                const item = document.createElement('div');
                item.className = 'data-item';
                item.innerHTML = `<strong>${key}</strong><span>${value}</span>`;
                extractedData.appendChild(item);
            }
        }
    };
    
    flattenData(data);
}

// Переключение JSON
toggleJsonBtn.addEventListener('click', () => {
    jsonResult.classList.toggle('hidden');
    toggleJsonBtn.textContent = jsonResult.classList.contains('hidden') 
        ? 'Показать JSON' 
        : 'Скрыть JSON';
});

// Скачивание JSON
downloadJsonBtn.addEventListener('click', () => {
    if (!currentJsonData) return;
    
    const dataStr = JSON.stringify(currentJsonData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ocr_result_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
});

// Новый документ
newDocumentBtn.addEventListener('click', () => {
    form.reset();
    fileInput.value = '';
    selectedFile = null;
    fileInfo.classList.add('hidden');
    resultsSection.classList.add('hidden');
    hideError();
    dropZone.scrollIntoView({ behavior: 'smooth' });
});

// Служебные функции
function showLoading() {
    loadingIndicator.classList.remove('hidden');
    loadingText.textContent = 'Обработка документа...';
}

function hideLoading() {
    loadingIndicator.classList.add('hidden');
}

function showError(message) {
    errorBox.classList.remove('hidden');
    errorMessage.textContent = message;
}

function hideError() {
    errorBox.classList.add('hidden');
}

function hideResults() {
    resultsSection.classList.add('hidden');
    jsonResult.classList.add('hidden');
    toggleJsonBtn.textContent = 'Показать JSON';
}

function openApiDocs() {
    window.open('/docs', '_blank');
}

// Установка API ключа из localStorage
window.addEventListener('load', () => {
    const savedApiKey = localStorage.getItem('apiKey');
    if (savedApiKey) {
        document.getElementById('apiKey').value = savedApiKey;
    }
});

// Сохранение API ключа
document.getElementById('apiKey').addEventListener('change', (e) => {
    localStorage.setItem('apiKey', e.target.value);
});
