from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ApontamentoHoras, Cliente, Maquina, Manutencao, Obra, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'perfil', 'is_active', 'is_staff']
    list_filter = ['perfil', 'is_active', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Perfil de acesso', {'fields': ('perfil', 'cpf')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Perfil de acesso', {'fields': ('email', 'perfil')}),
    )


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nome_fantasia', 'razao_social', 'cnpj', 'telefone', 'criado_em']
    search_fields = ['nome_fantasia', 'razao_social', 'cnpj']


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ['nome_obra', 'cliente', 'cidade', 'estado', 'status', 'data_inicio']
    list_filter = ['status', 'estado']
    search_fields = ['nome_obra', 'cidade']


@admin.register(Maquina)
class MaquinaAdmin(admin.ModelAdmin):
    list_display = ['prefixo', 'tipo', 'marca', 'modelo', 'horimetro_atual', 'status']
    list_filter = ['status', 'tipo']
    search_fields = ['prefixo', 'tipo', 'marca']


@admin.register(ApontamentoHoras)
class ApontamentoHorasAdmin(admin.ModelAdmin):
    list_display = ['data_apontamento', 'maquina', 'obra', 'total_horas', 'usuario']
    list_filter = ['data_apontamento']
    # Horímetros não são editáveis pelo admin para não quebrar a sequência
    readonly_fields = ['horimetro_inicial', 'horimetro_final', 'total_horas', 'criado_em']

    def has_add_permission(self, request):
        # Novos apontamentos devem passar pela tela do sistema (regra do horímetro)
        return False


@admin.register(Manutencao)
class ManutencaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'maquina', 'tipo', 'status', 'mecanico', 'data_inicio', 'data_conclusao']
    list_filter = ['status', 'tipo']
