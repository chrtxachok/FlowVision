"""
MinIO клиент для работы с объектным хранилищем.
"""

import io
import logging
from typing import Optional

import structlog
from minio import Minio
from minio.error import S3Error

logger = structlog.get_logger()


class MinioClient:
    """
    Клиент для работы с MinIO хранилищем.
    
    Операции:
    - Загрузка файлов
    - Скачивание файлов
    - Удаление файлов
    - Работа с преsigned URL
    """
    
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str = "documents",
        secure: bool = False,
        timeout: int = 300,
    ):
        """
        Инициализация MinIO клиента.
        
        Args:
            endpoint: Адрес MinIO сервера
            access_key: Ключ доступа
            secret_key: Секретный ключ
            bucket: Имя бакета
            secure: Использовать HTTPS
            timeout: Таймаут операций (сек)
        """
        self.bucket = bucket
        self.timeout = timeout
        
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        
        # Создание бакета, если не существует
        self._create_bucket_if_not_exists()
        
        logger.info(
            "MinIO client initialized",
            endpoint=endpoint,
            bucket=bucket,
        )
    
    def _create_bucket_if_not_exists(self) -> None:
        """Создание бакета, если он не существует."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Bucket {self.bucket} created")
        except S3Error as e:
            logger.error("Failed to create bucket", error=str(e))
    
    def check_connection(self) -> bool:
        """Проверка соединения с MinIO."""
        try:
            self.client.list_buckets()
            return True
        except S3Error as e:
            logger.error("MinIO connection check failed", error=str(e))
            return False
    
    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Загрузка файла в хранилище.
        
        Args:
            file_data: Данные файла
            object_name: Имя объекта в хранилище
            content_type: MIME тип файла
            
        Returns:
            Путь к загруженному файлу
        """
        try:
            file_size = len(file_data)
            data = io.BytesIO(file_data)
            
            self.client.put_object(
                self.bucket,
                object_name,
                data,
                file_size,
                content_type=content_type,
            )
            
            logger.info("File uploaded", object_name=object_name, size=file_size)
            return f"{self.bucket}/{object_name}"
            
        except S3Error as e:
            logger.error("File upload failed", object_name=object_name, error=str(e))
            raise
    
    def download_file(self, object_name: str) -> bytes:
        """
        Скачивание файла из хранилища.
        
        Args:
            object_name: Имя объекта
            
        Returns:
            Данные файла
        """
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info("File downloaded", object_name=object_name)
            return data
            
        except S3Error as e:
            logger.error("File download failed", object_name=object_name, error=str(e))
            raise
    
    def delete_file(self, object_name: str) -> bool:
        """
        Удаление файла из хранилища.
        
        Args:
            object_name: Имя объекта
            
        Returns:
            True при успехе
        """
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info("File deleted", object_name=object_name)
            return True
            
        except S3Error as e:
            logger.error("File deletion failed", object_name=object_name, error=str(e))
            return False
    
    def get_presigned_url(
        self,
        object_name: str,
        expires_hours: int = 1,
    ) -> str:
        """
        Получение преsigned URL для доступа к файлу.
        
        Args:
            object_name: Имя объекта
            expires_hours: Время жизни ссылки (часы)
            
        Returns:
            Преsigned URL
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=expires_hours * 3600,
            )
            
            logger.info("Presigned URL generated", object_name=object_name)
            return url
            
        except S3Error as e:
            logger.error("Presigned URL generation failed", error=str(e))
            raise
    
    def get_presigned_upload_url(
        self,
        object_name: str,
        expires_hours: int = 1,
    ) -> str:
        """
        Получение преsigned URL для загрузки файла.
        
        Args:
            object_name: Имя объекта
            expires_hours: Время жизни ссылки (часы)
            
        Returns:
            Преsigned URL
        """
        try:
            url = self.client.presigned_put_object(
                self.bucket,
                object_name,
                expires=expires_hours * 3600,
            )
            
            logger.info("Presigned upload URL generated", object_name=object_name)
            return url
            
        except S3Error as e:
            logger.error("Presigned upload URL generation failed", error=str(e))
            raise
    
    def file_exists(self, object_name: str) -> bool:
        """
        Проверка существования файла.
        
        Args:
            object_name: Имя объекта
            
        Returns:
            True если файл существует
        """
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False
    
    def list_files(self, prefix: str = "") -> list:
        """
        Список файлов в бакете.
        
        Args:
            prefix: Префикс для фильтрации
            
        Returns:
            Список объектов
        """
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error("Failed to list files", error=str(e))
            return []
