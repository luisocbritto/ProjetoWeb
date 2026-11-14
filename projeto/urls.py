from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Documentação da API (Swagger) para terceiros testarem
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),
    path('', include('terrasebritas.urls')),
]
