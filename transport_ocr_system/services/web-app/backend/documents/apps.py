"""Documents app configuration."""

from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    """Configuration for documents app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'documents'
    verbose_name = 'Документы'
