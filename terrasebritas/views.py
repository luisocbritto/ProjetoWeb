# =============================================================================
# views.py — cada função recebe o request do navegador e devolve uma resposta
# (página HTML com render, redirecionamento com redirect ou JSON).
#
#   1. Login             3. Obras (CRUD + busca)   5. API REST própria
#   2. Relatório         4. API externa ViaCEP
# =============================================================================
import re

import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, ProtectedError, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import ApontamentoHoras, Cliente, Maquina, Obra
from .serializers import ApontamentoSerializer, MaquinaSerializer, ObraSerializer


# =============================================================================
# 1. LOGIN
# =============================================================================

def login_view(request):
    if request.method == 'POST':
        # authenticate confere usuário e senha (a senha é guardada com hash)
        usuario = authenticate(request, username=request.POST.get('username'),
                               password=request.POST.get('password'))
        if usuario is not None:
            login(request, usuario)  # cria a sessão
            return redirect('relatorio')
        messages.error(request, 'Usuário ou senha inválidos.')
    return render(request, 'sgcc/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# =============================================================================
# 2. RELATÓRIO CONSOLIDADO (página inicial)
#   aggregate        -> um resultado para todos os registros (totais gerais)
#   values + annotate -> agrupa (GROUP BY) e calcula por grupo
# =============================================================================

@login_required  # sem login, redireciona para a tela de login
def relatorio(request):
    apontamentos = ApontamentoHoras.objects.all()

    return render(request, 'sgcc/relatorio.html', {
        'totais': apontamentos.aggregate(horas=Sum('total_horas'), quantidade=Count('id')),
        'por_obra': apontamentos.values('obra__nome_obra')
                                .annotate(horas=Sum('total_horas'), quantidade=Count('id'))
                                .order_by('-horas'),
        'por_maquina': apontamentos.values('maquina__prefixo')
                                   .annotate(horas=Sum('total_horas'), quantidade=Count('id'))
                                   .order_by('-horas'),
    })


# =============================================================================
# 3. OBRAS — listar com busca, cadastrar/editar (mesmo formulário) e excluir
# =============================================================================

@login_required
def listar_obras(request):
    busca = request.GET.get('busca', '')
    obras = Obra.objects.select_related('cliente')
    if busca:
        # icontains = "contém", sem diferenciar maiúsculas. Q permite usar OU (|)
        obras = obras.filter(Q(nome_obra__icontains=busca) | Q(cidade__icontains=busca))
    return render(request, 'sgcc/listar_obras.html', {'obras': obras, 'busca': busca})


@login_required
def form_obra(request, id=None):
    # Sem id = cadastrar uma obra nova; com id = editar uma obra existente
    obra = get_object_or_404(Obra, id=id) if id else Obra()
    erros = {}

    if request.method == 'POST':
        obra.cliente_id = request.POST.get('cliente_id')
        obra.nome_obra = request.POST.get('nome_obra', '').strip()
        obra.cep = re.sub(r'\D', '', request.POST.get('cep', ''))  # deixa só os números
        obra.logradouro = request.POST.get('logradouro', '').strip()
        obra.numero = request.POST.get('numero', '').strip()
        obra.bairro = request.POST.get('bairro', '').strip()
        obra.cidade = request.POST.get('cidade', '').strip()
        obra.estado = request.POST.get('estado', '').strip().upper()
        obra.status = request.POST.get('status')
        obra.data_inicio = request.POST.get('data_inicio')

        try:
            # full_clean valida pelo model: obrigatórios, tamanhos, choices, data e cliente
            obra.full_clean()
            obra.save()
            messages.success(request, 'Obra salva com sucesso.')
            return redirect('listar_obras')
        except ValidationError as erro:
            erros = erro.message_dict  # {campo: [mensagens]} para mostrar no formulário

    return render(request, 'sgcc/form_obra.html', {
        'obra': obra,
        'erros': erros,
        'clientes': Cliente.objects.all(),
        'status_choices': Obra.STATUS_CHOICES,
    })


@login_required
@require_POST  # só exclui por POST (botão com csrf_token), nunca por um link
def deletar_obra(request, id):
    obra = get_object_or_404(Obra, id=id)
    try:
        obra.delete()
        messages.success(request, 'Obra excluída.')
    except ProtectedError:
        # on_delete=PROTECT: obra com apontamentos não pode ser apagada
        messages.error(request, 'Esta obra tem apontamentos e não pode ser excluída.')
    return redirect('listar_obras')


# =============================================================================
# 4. API EXTERNA — ViaCEP (https://viacep.com.br)
# Chamada pelo botão "Buscar CEP" do formulário de obra (JavaScript)
# =============================================================================

@login_required
def buscar_cep(request):
    cep = re.sub(r'\D', '', request.GET.get('cep', ''))
    if len(cep) != 8:
        return JsonResponse({'erro': 'O CEP deve ter 8 dígitos.'}, status=400)

    try:
        # timeout=5: se o ViaCEP não responder em 5 segundos, desiste
        resposta = requests.get(f'https://viacep.com.br/ws/{cep}/json/', timeout=5)
        resposta.raise_for_status()  # erro se o status HTTP for 4xx/5xx
        dados = resposta.json()      # erro se a resposta não for JSON
    except requests.exceptions.Timeout:
        return JsonResponse({'erro': 'O ViaCEP demorou para responder.'}, status=504)
    except (requests.exceptions.RequestException, ValueError):
        return JsonResponse({'erro': 'Não foi possível consultar o CEP.'}, status=502)

    if dados.get('erro'):  # CEP inexistente: o ViaCEP responde {"erro": true}
        return JsonResponse({'erro': 'CEP não encontrado.'}, status=404)

    # Devolve só o que o formulário usa, já com os nomes dos nossos campos
    return JsonResponse({
        'logradouro': dados.get('logradouro', ''),
        'bairro': dados.get('bairro', ''),
        'cidade': dados.get('localidade', ''),
        'estado': dados.get('uf', ''),
    })


# =============================================================================
# 5. API REST PRÓPRIA (Django REST Framework) — /api/v1/
# ModelViewSet já cria: listar (GET), detalhar (GET /id/), criar (POST),
# alterar (PUT/PATCH) e excluir (DELETE). Exige login por JWT (settings.py).
# =============================================================================

class ObraViewSet(viewsets.ModelViewSet):
    queryset = Obra.objects.all()
    serializer_class = ObraSerializer

    def destroy(self, request, *args, **kwargs):
        # Obra com apontamentos: responde 409 (conflito) em vez de erro 500
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response({'detail': 'Obra possui apontamentos.'}, status=status.HTTP_409_CONFLICT)


class MaquinaViewSet(viewsets.ReadOnlyModelViewSet):
    # Só consulta (GET): serve para ver o horímetro atual das máquinas
    queryset = Maquina.objects.all()
    serializer_class = MaquinaSerializer


class ApontamentoViewSet(viewsets.ModelViewSet):
    queryset = ApontamentoHoras.objects.all()
    serializer_class = ApontamentoSerializer
    http_method_names = ['get', 'post']  # consulta e registra (a regra está no serializer)
