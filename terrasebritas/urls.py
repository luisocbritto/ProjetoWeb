from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

# Rotas da API REST própria: /api/v1/<recurso>/
router = DefaultRouter()
router.register('clientes', views.ClienteViewSet, basename='api-clientes')
router.register('obras', views.ObraViewSet, basename='api-obras')
router.register('maquinas', views.MaquinaViewSet, basename='api-maquinas')
router.register('apontamentos', views.ApontamentoViewSet, basename='api-apontamentos')
router.register('manutencoes', views.ManutencaoViewSet, basename='api-manutencoes')

urlpatterns = [
    # Dashboard, autenticação e institucional
    path('', views.index, name='index'),
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('sobre', views.sobre, name='sobre'),

    # Clientes
    path('listar_clientes', views.listar_clientes, name='listar_clientes'),
    path('detalhar_cliente/<int:id>', views.detalhar_cliente, name='detalhar_cliente'),
    path('cadastrar_cliente', views.cadastrar_cliente, name='cadastrar_cliente'),
    path('editar_cliente/<int:id>', views.editar_cliente, name='editar_cliente'),
    path('deletar_cliente/<int:id>', views.deletar_cliente, name='deletar_cliente'),

    # Obras
    path('listar_obras', views.listar_obras, name='listar_obras'),
    path('detalhar_obra/<int:id>', views.detalhar_obra, name='detalhar_obra'),
    path('cadastrar_obra', views.cadastrar_obra, name='cadastrar_obra'),
    path('editar_obra/<int:id>', views.editar_obra, name='editar_obra'),
    path('deletar_obra/<int:id>', views.deletar_obra, name='deletar_obra'),

    # Máquinas
    path('listar_maquinas', views.listar_maquinas, name='listar_maquinas'),
    path('detalhar_maquina/<int:id>', views.detalhar_maquina, name='detalhar_maquina'),
    path('cadastrar_maquina', views.cadastrar_maquina, name='cadastrar_maquina'),
    path('editar_maquina/<int:id>', views.editar_maquina, name='editar_maquina'),
    path('deletar_maquina/<int:id>', views.deletar_maquina, name='deletar_maquina'),

    # Apontamentos de horas
    path('listar_apontamentos', views.listar_apontamentos, name='listar_apontamentos'),
    path('detalhar_apontamento/<int:id>', views.detalhar_apontamento, name='detalhar_apontamento'),
    path('cadastrar_apontamento', views.cadastrar_apontamento, name='cadastrar_apontamento'),
    path('editar_apontamento/<int:id>', views.editar_apontamento, name='editar_apontamento'),
    path('deletar_apontamento/<int:id>', views.deletar_apontamento, name='deletar_apontamento'),

    # Manutenções
    path('listar_manutencoes', views.listar_manutencoes, name='listar_manutencoes'),
    path('detalhar_manutencao/<int:id>', views.detalhar_manutencao, name='detalhar_manutencao'),
    path('cadastrar_manutencao', views.cadastrar_manutencao, name='cadastrar_manutencao'),
    path('editar_manutencao/<int:id>', views.editar_manutencao, name='editar_manutencao'),
    path('deletar_manutencao/<int:id>', views.deletar_manutencao, name='deletar_manutencao'),

    # Relatório consolidado
    path('relatorio_horas', views.relatorio_horas, name='relatorio_horas'),
    path('exportar_relatorio_csv', views.exportar_relatorio_csv, name='exportar_relatorio_csv'),

    # API externa ViaCEP
    path('consultar_cep', views.consultar_cep, name='consultar_cep'),
    path('buscar_cep_json', views.buscar_cep_json, name='buscar_cep_json'),

    # API REST própria (JWT)
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/', include(router.urls)),
]
