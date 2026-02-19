from minio import Minio
from minio.error import S3Error
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


class MinioClient:
    """Client for MinIO/S3 storage operations"""
    
    def __init__(self, settings):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET
        
        # Ensure bucket exists
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
            logger.info(f"Created bucket: {self.bucket}")
    
    def download_file(self, file_path: str) -> str:
        """
        Download file from MinIO to local temporary storage
        
        Args:
            file_path: Path to file in MinIO bucket
            
        Returns:
            Local path to downloaded file
        """
        try:
            # Create temporary file
            temp_dir = '/tmp/ocr_processing'
            os.makedirs(temp_dir, exist_ok=True)
            
            local_path = os.path.join(temp_dir, os.path.basename(file_path))
            
            # Download file
            self.client.fget_object(
                bucket_name=self.bucket,
                object_name=file_path,
                file_path=local_path
            )
            
            logger.info(f"Downloaded {file_path} to {local_path}")
            return local_path
            
        except S3Error as e:
            logger.error(f"Error downloading file {file_path}: {e}")
            raise
    
    def upload_file(self, local_path: str, file_path: str) -> str:
        """
        Upload file to MinIO storage
        
        Args:
            local_path: Local path to file
            file_path: Path in MinIO bucket
            
        Returns:
            Object name in MinIO
        """
        try:
            # Upload file
            self.client.fput_object(
                bucket_name=self.bucket,
                object_name=file_path,
                file_path=local_path
            )
            
            logger.info(f"Uploaded {local_path} to {file_path}")
            return file_path
            
        except S3Error as e:
            logger.error(f"Error uploading file {local_path}: {e}")
            raise
    
    def get_file_url(self, file_path: str, expires: int = 3600) -> str:
        """
        Get presigned URL for file access
        
        Args:
            file_path: Path to file in MinIO
            expires: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        try:
            return self.client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=file_path,
                expires=expires
            )
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise