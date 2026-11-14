from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView

from . import views

# O router cria as rotas da API: /api/v1/obras/, /api/v1/obras/<id>/ etc.
router = DefaultRouter()
router.register('obras', views.ObraViewSet)
router.register('maquinas', views.MaquinaViewSet)
router.register('apontamentos', views.ApontamentoViewSet)

urlpatterns = [
    # Login e relatório (página inicial)
    path('', views.relatorio, name='relatorio'),
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),

    # Obras (CRUD com busca)
    path('listar_obras', views.listar_obras, name='listar_obras'),
    path('cadastrar_obra', views.form_obra, name='cadastrar_obra'),
    path('editar_obra/<int:id>', views.form_obra, name='editar_obra'),
    path('deletar_obra/<int:id>', views.deletar_obra, name='deletar_obra'),

    # API externa (ViaCEP), chamada pelo formulário de obra
    path('buscar_cep', views.buscar_cep, name='buscar_cep'),

    # API REST própria: primeiro pegue o token, depois use as rotas do router
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token'),
    path('api/v1/', include(router.urls)),
]
