# Cadastros de apoio (usuários, clientes e máquinas) ficam no painel /admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Cliente, Maquina, Usuario

admin.site.register(Usuario, UserAdmin)
admin.site.register(Cliente)
admin.site.register(Maquina)
