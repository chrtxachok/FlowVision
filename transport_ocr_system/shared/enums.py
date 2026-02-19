"""
Общие перечисления для транспортной OCR системы.
"""

from enum import Enum


class DocumentType(str, Enum):
    """Типы поддерживаемых документов."""
    TRANSPORT_WAYBILL = "transport_waybill"       # Транспортная накладная
    BILL_OF_LADING = "bill_of_lading"              # Коносамент
    INVOICE = "invoice"                            # Счет-фактура
    PACKING_LIST = "packing_list"                  # Упаковочный лист
    CUSTOM_DECLARATION = "custom_declaration"      # Таможенная декларация
    DRIVER_LICENSE = "driver_license"               # Водительское удостоверение
    VEHICLE_REGISTRATION = "vehicle_registration"   # Регистрация ТС
    UNKNOWN = "unknown"


class ProcessingStatus(str, Enum):
    """Статусы обработки документов."""
    PENDING = "pending"                     # Ожидает обработки
    QUEUED = "queued"                       # В очереди на обработку
    PROCESSING = "processing"               # В процессе обработки
    COMPLETED = "completed"                 # Успешно обработан
    FAILED = "failed"                       # Ошибка обработки
    PARTIAL_SUCCESS = "partial_success"     # Частично обработан


class FieldType(str, Enum):
    """Типы полей в документах."""
    TEXT = "text"                           # Простой текст
    TABLE = "table"                        # Таблица
    DATE = "date"                           # Дата
    NUMBER = "number"                       # Число
    ADDRESS = "address"                     # Адрес
    PHONE = "phone"                         # Телефон
    EMAIL = "email"                         # Email
    INN = "inn"                             # ИНН
    KPP = "kpp"                             # КПП
    OKPO = "okpo"                           # ОКПО
    BANK_ACCOUNT = "bank_account"           # Банковский счет
    BIK = "bik"                             # БИК
    VIN = "vin"                             # VIN номер ТС
    LICENSE_PLATE = "license_plate"        # Гос. номер
    TRAILER_NUMBER = "trailer_number"      # Номер прицепа


class ConfidenceLevel(str, Enum):
    """Уровень достоверности распознавания."""
    HIGH = "high"           # > 0.9
    MEDIUM = "medium"       # 0.7 - 0.9
    LOW = "low"             # < 0.7
