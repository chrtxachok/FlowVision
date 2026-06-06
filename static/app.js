// ============================================================
// FlowLogix OCR — фронтенд
// Работает с движком logika.WaybillExtractor (как в test_gui.py):
//   - страница 1 (обязательно) + страница 2 (опционально)
//   - ответ: { status, document_type, processing_time_ms, pages_processed, extracted_data }
//   - extracted_data — плоский словарь полей F001..F021
// ============================================================

// Человеко-читаемые названия полей накладной (как извлекает logika.py)
const FIELD_LABELS = {
    F001: 'Номер накладной',
    F002: 'Дата',
    F003: 'Грузоотправитель',
    F004: 'Грузополучатель',
    F005: 'Стоимость',
    F006: 'Наименование груза',
    F007: 'Перевозчик',
    F008: 'ИНН грузоотправителя',
    F009: 'ИНН грузополучателя',
    F010: 'КПП грузоотправителя',
    F011: 'КПП грузополучателя',
    F013: 'Заказ (заявка) №',
    F014: 'Документ №',
    F015: 'Дата/время погрузки',
    F016: 'Дата/время выгрузки',
    F017: 'ИНН перевозчика',
    F018: 'ФИО водителя',
    F019: 'Гос. номер ТС',
    F020: 'Реквизиты (стр. 2)',
    F021: 'Реквизиты (стр. 2)',
};

// Элементы DOM
const form = document.getElementById('uploadForm');
const dropZone = document.getElementById('dropZone');
const dropZone2 = document.getElementById('dropZone2');
const fileInput = document.getElementById('fileInput');
const fileInput2 = document.getElementById('fileInput2');
const fileName1 = document.getElementById('fileName1');
const fileName2 = document.getElementById('fileName2');
const submitBtn = document.getElementById('submitBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const loadingText = document.getElementById('loadingText');
const resultsSection = document.getElementById('resultsSection');
const errorBox = document.getElementById('errorBox');
const errorMessage = document.getElementById('errorMessage');
const statusBox = document.getElementById('statusBox');
const statusIcon = document.getElementById('statusIcon');
const statusText = document.getElementById('statusText');
const processingTime = document.getElementById('processingTime');
const extractedData = document.getElementById('extractedData');
const jsonResult = document.getElementById('jsonResult');
const toggleJsonBtn = document.getElementById('toggleJsonBtn');
const downloadJsonBtn = document.getElementById('downloadJsonBtn');
const newDocumentBtn = document.getElementById('newDocumentBtn');

let currentJsonData = null;
let selectedFile = null;   // страница 1
let selectedFile2 = null;  // страница 2 (опционально)

const VALID_TYPES = ['image/jpeg', 'image/png', 'image/bmp', 'image/tiff'];
const MAX_SIZE = 10 * 1024 * 1024;

// ---- Drag-and-drop / выбор файлов ----
function wireDropZone(zone, input, page) {
    zone.addEventListener('click', () => input.click());
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0], page);
        }
    });
    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0], page);
        }
    });
}

wireDropZone(dropZone, fileInput, 1);
wireDropZone(dropZone2, fileInput2, 2);

function validateFile(file) {
    if (!VALID_TYPES.includes(file.type)) {
        showError('Неподдерживаемый формат файла. Используйте JPG, PNG, BMP или TIFF');
        return false;
    }
    if (file.size > MAX_SIZE) {
        showError(`Файл слишком большой (макс. 10 МБ). Текущий размер: ${(file.size / 1024 / 1024).toFixed(2)} МБ`);
        return false;
    }
    return true;
}

function handleFileSelect(file, page) {
    if (!validateFile(file)) return;

    if (page === 1) {
        selectedFile = file;
        fileName1.textContent = `✓ ${file.name} (${(file.size / 1024).toFixed(1)} КБ)`;
    } else {
        selectedFile2 = file;
        fileName2.textContent = `✓ ${file.name} (${(file.size / 1024).toFixed(1)} КБ)`;
    }

    hideResults();
    hideError();
}

// ---- Отправка формы ----
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!selectedFile) {
        showError('Пожалуйста, выберите хотя бы страницу 1');
        return;
    }
    await processDocument();
});

async function processDocument() {
    const documentType = document.getElementById('documentType').value;
    const apiKey = document.getElementById('apiKey').value;

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (selectedFile2) {
        formData.append('file2', selectedFile2);
    }
    formData.append('document_type', documentType);
    formData.append('api_key', apiKey);

    showLoading();
    submitBtn.disabled = true;
    hideError();
    hideResults();

    try {
        const startTime = Date.now();
        const response = await fetch('/api/v1/ocr/process', {
            method: 'POST',
            body: formData,
        });
        const processingTimeMs = Date.now() - startTime;

        if (!response.ok) {
            let detail = `Ошибка сервера (${response.status})`;
            try {
                const error = await response.json();
                detail = error.detail || error.message || detail;
            } catch (_) { /* ignore */ }
            throw new Error(detail);
        }

        const data = await response.json();
        currentJsonData = data;

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
    if (data.status === 'success') {
        statusIcon.textContent = '✓';
        statusIcon.style.color = '#10b981';
        statusText.textContent = 'Успешно обработано';
    } else if (data.status === 'partial') {
        statusIcon.textContent = '⚠️';
        statusIcon.style.color = '#f59e0b';
        statusText.textContent = 'Обработано частично';
    } else {
        statusIcon.textContent = '✕';
        statusIcon.style.color = '#ef4444';
        statusText.textContent = 'Ничего не распознано';
    }

    const serverMs = data.processing_time_ms != null ? data.processing_time_ms : processingTimeMs;
    const pages = data.pages_processed != null ? `, страниц: ${data.pages_processed}` : '';
    processingTime.textContent = `⏱️ ${(serverMs / 1000).toFixed(2)}s${pages}`;

    displayExtractedData(data.extracted_data);

    jsonResult.textContent = JSON.stringify(data, null, 2);
    resultsSection.classList.remove('hidden');
    setTimeout(() => resultsSection.scrollIntoView({ behavior: 'smooth' }), 100);
}

function displayExtractedData(data) {
    extractedData.innerHTML = '';

    if (!data || Object.keys(data).length === 0) {
        extractedData.innerHTML = '<div class="data-item null"><strong>Поля не найдены</strong></div>';
        return;
    }

    // Сортируем поля по их коду (F001, F002, ...)
    const keys = Object.keys(data).sort();
    for (const key of keys) {
        const value = data[key];
        const label = FIELD_LABELS[key] || key;
        const item = document.createElement('div');

        if (value === null || value === undefined || value === '') {
            item.className = 'data-item null';
            item.innerHTML = `<strong>${label} <small>(${key})</small></strong><span>(не найдено)</span>`;
        } else {
            item.className = 'data-item';
            item.innerHTML = `<strong>${label} <small>(${key})</small></strong><span>${escapeHtml(String(value))}</span>`;
        }
        extractedData.appendChild(item);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ---- JSON-секция ----
toggleJsonBtn.addEventListener('click', () => {
    jsonResult.classList.toggle('hidden');
    toggleJsonBtn.textContent = jsonResult.classList.contains('hidden')
        ? 'Показать JSON'
        : 'Скрыть JSON';
});

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

newDocumentBtn.addEventListener('click', () => {
    form.reset();
    fileInput.value = '';
    fileInput2.value = '';
    selectedFile = null;
    selectedFile2 = null;
    fileName1.textContent = '';
    fileName2.textContent = '';
    resultsSection.classList.add('hidden');
    hideError();
    dropZone.scrollIntoView({ behavior: 'smooth' });
});

// ---- Служебные функции ----
function showLoading() {
    loadingIndicator.classList.remove('hidden');
    loadingText.textContent = 'Распознавание... это может занять до минуты';

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

// ---- API ключ из localStorage ----
// Подставляем сохранённый ключ только если он непустой;
// иначе оставляем корректное значение по умолчанию из HTML.
window.addEventListener('load', () => {
    const savedApiKey = localStorage.getItem('apiKey');
    if (savedApiKey && savedApiKey.trim()) {
        document.getElementById('apiKey').value = savedApiKey.trim();
    }
});
document.getElementById('apiKey').addEventListener('change', (e) => {
    const val = e.target.value.trim();
    if (val) {
        localStorage.setItem('apiKey', val);
    } else {
        // Пустой ключ не сохраняем — чистим, чтобы вернулось значение по умолчанию
        localStorage.removeItem('apiKey');
    }
});


