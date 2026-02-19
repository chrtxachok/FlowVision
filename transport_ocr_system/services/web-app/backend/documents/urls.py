"""URL configuration for documents app."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, DocumentFieldViewSet

router = DefaultRouter()
router.register(r'', DocumentViewSet, basename='document')
router.register(r'fields', DocumentFieldViewSet, basename='document-field')

urlpatterns = [
    path('', include(router.urls)),
]
