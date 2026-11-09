from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Documentação da API REST (OpenAPI 3)
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='api_schema'), name='api_redoc'),

    # Aplicação web e API REST
    path('', include('terrasebritas.urls')),
]
