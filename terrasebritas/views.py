"""
Views do sistema Ás Terraplanagem — Gestão Operacional.

Organização deste arquivo:
1. Funções auxiliares
2. Autenticação, dashboard e página Sobre
3. CRUD de Clientes
4. CRUD de Obras (com preenchimento de endereço pelo ViaCEP)
5. CRUD de Máquinas
6. CRUD de Apontamentos de horas
7. CRUD de Manutenções
8. Relatório consolidado de horas (tela, impressão e CSV)
9. Consumo da API externa ViaCEP
10. API REST própria (ViewSets do Django REST Framework)
"""
import csv

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Avg, Count, ProtectedError, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from .models import (
    PERFIS_APONTAMENTO,
    PERFIS_CADASTRO,
    PERFIS_MANUTENCAO,
    PERFIS_SOMENTE_ADMIN,
    ApontamentoHoras,
    Cliente,
    Maquina,
    Manutencao,
    Obra,
    Usuario,
    abrir_manutencao,
    atualizar_manutencao,
    excluir_apontamento,
    excluir_manutencao,
    registrar_apontamento,
)
from .serializers import (
    ApontamentoSerializer,
    ClienteSerializer,
    MaquinaSerializer,
    ManutencaoSerializer,
    ObraSerializer,
)
from .validacoes import (
    ESTADOS_BRASIL,
    cnpj_valido,
    converter_data,
    converter_decimal,
    email_valido,
    somente_digitos,
)
from .viacep import consultar_viacep


# =============================================================================
# 1. Funções auxiliares
# =============================================================================

def sem_permissao(request, rota):
    """Mostra a mensagem de perfil sem permissão e volta para a rota informada."""
    messages.error(request, 'Seu perfil não tem permissão para realizar esta operação.')
    return redirect(rota)


def paginar(request, lista, por_pagina=10):
    """Divide a lista em páginas usando o parâmetro ?page= da URL."""
    paginador = Paginator(lista, por_pagina)
    return paginador.get_page(request.GET.get('page'))


def parametros_sem_pagina(request):
    """Mantém os filtros da busca ao trocar de página."""
    parametros = request.GET.copy()
    parametros.pop('page', None)
    return parametros.urlencode()


def filtrar_apontamentos(request):
    """
    Aplica os filtros de obra, máquina e período usados na listagem de
    apontamentos, no relatório e na exportação CSV.
    """
    apontamentos = ApontamentoHoras.objects.select_related(
        'obra', 'obra__cliente', 'maquina', 'usuario'
    )

    filtros = {
        'obra': request.GET.get('obra', '').strip(),
        'maquina': request.GET.get('maquina', '').strip(),
        'data_inicio': request.GET.get('data_inicio', '').strip(),
        'data_fim': request.GET.get('data_fim', '').strip(),
    }

    if filtros['obra'].isdigit():
        apontamentos = apontamentos.filter(obra_id=int(filtros['obra']))

    if filtros['maquina'].isdigit():
        apontamentos = apontamentos.filter(maquina_id=int(filtros['maquina']))

    data_inicio = converter_data(filtros['data_inicio'])
    if data_inicio:
        apontamentos = apontamentos.filter(data_apontamento__gte=data_inicio)

    data_fim = converter_data(filtros['data_fim'])
    if data_fim:
        apontamentos = apontamentos.filter(data_apontamento__lte=data_fim)

    return apontamentos, filtros


# =============================================================================
# 2. Autenticação, dashboard e Sobre
# =============================================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    proximo = request.GET.get('next', '') or request.POST.get('next', '')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        senha = request.POST.get('password', '')
        usuario = authenticate(request, username=username, password=senha)

        if usuario is not None:
            login(request, usuario)
            messages.success(request, f'Bem-vindo(a), {usuario}!')
            if proximo and url_has_allowed_host_and_scheme(proximo, allowed_hosts={request.get_host()},
                                                           require_https=request.is_secure()):
                return redirect(proximo)
            return redirect('index')

        messages.error(request, 'Usuário ou senha inválidos.')

    return render(request, 'sgcc/login.html', {'proximo': proximo})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Você saiu do sistema.')
    return redirect('login')


@login_required
def index(request):
    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)

    horas_mes = ApontamentoHoras.objects.filter(
        data_apontamento__gte=inicio_mes
    ).aggregate(total=Sum('total_horas'))['total'] or 0

    contexto = {
        'maquinas_disponiveis': Maquina.objects.filter(status='DISPONIVEL').count(),
        'maquinas_em_uso': Maquina.objects.filter(status='EM_USO').count(),
        'maquinas_manutencao': Maquina.objects.filter(status='MANUTENCAO').count(),
        'obras_andamento': Obra.objects.filter(status='EM_ANDAMENTO').count(),
        'total_clientes': Cliente.objects.count(),
        'horas_mes': horas_mes,
        'inicio_mes': inicio_mes,
        'apontamentos_recentes': ApontamentoHoras.objects.select_related('obra', 'maquina')[:8],
        'manutencoes_abertas': Manutencao.objects.filter(
            status__in=['ABERTA', 'EM_ANDAMENTO']
        ).select_related('maquina', 'mecanico')[:5],
    }
    return render(request, 'sgcc/index.html', contexto)


def sobre(request):
    integrantes = ['Cauã Medeiros', 'Luis Otávio', 'João Lucas']
    return render(request, 'sgcc/sobre.html', {'integrantes': integrantes})


# =============================================================================
# 3. CRUD de Clientes
# =============================================================================

CAMPOS_CLIENTE = ['razao_social', 'nome_fantasia', 'cnpj', 'telefone', 'email']


def ler_dados_cliente(request):
    return {campo: request.POST.get(campo, '').strip() for campo in CAMPOS_CLIENTE}


def validar_cliente(dados, cliente_id=None):
    erros = {}

    if not dados['razao_social']:
        erros['razao_social'] = 'Informe a razão social.'
    elif len(dados['razao_social']) > 200:
        erros['razao_social'] = 'A razão social deve ter no máximo 200 caracteres.'

    if not dados['nome_fantasia']:
        erros['nome_fantasia'] = 'Informe o nome fantasia.'
    elif len(dados['nome_fantasia']) > 200:
        erros['nome_fantasia'] = 'O nome fantasia deve ter no máximo 200 caracteres.'

    cnpj = somente_digitos(dados['cnpj'])
    if not cnpj_valido(cnpj):
        erros['cnpj'] = 'CNPJ inválido. Confira os 14 dígitos.'
    elif Cliente.objects.filter(cnpj=cnpj).exclude(id=cliente_id).exists():
        erros['cnpj'] = 'Já existe um cliente cadastrado com este CNPJ.'

    if len(dados['telefone']) > 20:
        erros['telefone'] = 'O telefone deve ter no máximo 20 caracteres.'

    if dados['email'] and not email_valido(dados['email']):
        erros['email'] = 'Informe um e-mail válido.'

    return erros


@login_required
def listar_clientes(request):
    busca = request.GET.get('busca', '').strip()
    clientes = Cliente.objects.annotate(qtd_obras=Count('obras'))

    if busca:
        filtro = Q(razao_social__icontains=busca) | Q(nome_fantasia__icontains=busca)
        digitos = somente_digitos(busca)
        if digitos:
            filtro = filtro | Q(cnpj__icontains=digitos)
        clientes = clientes.filter(filtro)

    contexto = {
        'clientes': paginar(request, clientes),
        'busca': busca,
        'parametros': parametros_sem_pagina(request),
    }
    return render(request, 'sgcc/listar_clientes.html', contexto)


@login_required
def detalhar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    obras = cliente.obras.annotate(horas=Sum('apontamentos__total_horas'))
    return render(request, 'sgcc/detalhar_cliente.html', {'cliente': cliente, 'obras': obras})


@login_required
def cadastrar_cliente(request):
    if not request.user.tem_perfil(PERFIS_CADASTRO):
        return sem_permissao(request, 'listar_clientes')

    dados = {}
    erros = {}

    if request.method == 'POST':
        dados = ler_dados_cliente(request)
        erros = validar_cliente(dados)

        if not erros:
            cliente = Cliente.objects.create(
                razao_social=dados['razao_social'],
                nome_fantasia=dados['nome_fantasia'],
                cnpj=somente_digitos(dados['cnpj']),
                telefone=dados['telefone'],
                email=dados['email'],
            )
            messages.success(request, 'Cliente cadastrado com sucesso.')
            return redirect('detalhar_cliente', id=cliente.id)

        messages.error(request, 'Corrija os campos destacados.')

    return render(request, 'sgcc/form_cliente.html', {
        'dados': dados, 'erros': erros, 'titulo': 'Novo cliente',
    })


@login_required
def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    if not request.user.tem_perfil(PERFIS_CADASTRO):
        return sem_permissao(request, 'listar_clientes')

    dados = {campo: getattr(cliente, campo) for campo in CAMPOS_CLIENTE}
    dados['cnpj'] = cliente.cnpj_formatado
    erros = {}

    if request.method == 'POST':
        dados = ler_dados_cliente(request)
        erros = validar_cliente(dados, cliente_id=cliente.id)

        if not erros:
            cliente.razao_social = dados['razao_social']
            cliente.nome_fantasia = dados['nome_fantasia']
            cliente.cnpj = somente_digitos(dados['cnpj'])
            cliente.telefone = dados['telefone']
            cliente.email = dados['email']
            cliente.save()
            messages.success(request, 'Cliente atualizado com sucesso.')
            return redirect('detalhar_cliente', id=cliente.id)

        messages.error(request, 'Corrija os campos destacados.')

    return render(request, 'sgcc/form_cliente.html', {
        'dados': dados, 'erros': erros, 'titulo': 'Editar cliente', 'cliente': cliente,
    })


@login_required
def deletar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    if not request.user.tem_perfil(PERFIS_CADASTRO):
        return sem_permissao(request, 'listar_clientes')

    if request.method == 'POST':
        try:
            cliente.delete()
            messages.success(request, 'Cliente excluído com sucesso.')
            return redirect('listar_clientes')
        except ProtectedError:
            messages.error(request, 'Este cliente possui obras vinculadas e não pode ser excluído.')
            return redirect('detalhar_cliente', id=cliente.id)

    return render(request, 'sgcc/confirmar_deletar.html', {
        'tipo': 'cliente',
        'nome': f'{cliente.nome_fantasia} ({cliente.cnpj_formatado})',
        'url_cancelar': reverse('detalhar_cliente', args=[cliente.id]),
    })


# =============================================================================
# 4. CRUD de Obras
# =============================================================================

CAMPOS_OBRA = ['cliente_id', 'nome_obra', 'cep', 'logradouro', 'numero', 'bairro',
               'cidade', 'estado', 'status', 'data_inicio']


def ler_dados_obra(request):
    return {campo: request.POST.get(campo, '').strip() for campo in CAMPOS_OBRA}


def validar_obra(dados):
    """Valida os dados da obra e completa o endereço pelo ViaCEP se faltar cidade/UF."""
    erros = {}

    if not dados['cliente_id'].isdigit() or not Cliente.objects.filter(id=int(dados['cliente_id'])).exists():
        erros['cliente_id'] = 'Selecione um cliente válido.'

    if not dados['nome_obra']:
        erros['nome_obra'] = 'Informe o nome da obra.'
    elif len(dados['nome_obra']) > 150:
        erros['nome_obra'] = 'O nome da obra deve ter no máximo 150 caracteres.'

    dados['cep'] = somente_digitos(dados['cep'])
    if len(dados['cep']) != 8:
        erros['cep'] = 'Informe um CEP com 8 dígitos.'
    elif not dados['cidade'] or not dados['estado']:
        # Endereço incompleto: tenta preencher pelo ViaCEP no servidor
        endereco, erro = consultar_viacep(dados['cep'])
        if endereco:
            for campo in ['logradouro', 'bairro', 'cidade', 'estado']:
                if not dados[campo]:
                    dados[campo] = endereco[campo]
        else:
            erros['cep'] = f'{erro} Se preferir, preencha cidade e UF manualmente.'

    dados['estado'] = dados['estado'].upper()
    if not dados['cidade']:
        erros['cidade'] = 'Informe a cidade.'
    if dados['estado'] not in ESTADOS_BRASIL:
        erros['estado'] = 'Selecione uma UF válida.'

    if len(dados['logradouro']) > 200:
        erros['logradouro'] = 'O logradouro deve ter no máximo 200 caracteres.'
    if len(dados['numero']) > 20:
        erros['numero'] = 'O número deve ter no máximo 20 caracteres.'
    if len(dados['bairro']) > 100:
        erros['bairro'] = 'O bairro deve ter no máximo 100 caracteres.'

    if dados['status'] not in dict(Obra.STATUS_CHOICES):
        erros['status'] = 'Selecione um status válido.'

    if not converter_data(dados['data_inicio']):
        erros['data_inicio'] = 'Informe uma data de início válida.'

    return erros


def contexto_form_obra(dados, erros, titulo, obra=None):
    return {
        'dados': dados,
        'erros': erros,
        'titulo': titulo,
        'obra': obra,
        'clientes': Cliente.objects.all(),
        'status_choices': Obra.STATUS_CHOICES,
        'estados': ESTADOS_BRASIL,
    }


def salvar_campos_obra(obra, dados):
    obra.cliente_id = int(dados['cliente_id'])
    obra.nome_obra = dados['nome_obra']
    obra.cep = dados['cep']
    obra.logradouro = dados['logradouro']
    obra.numero = dados['numero']
    obra.bairro = dados['bairro']
    obra.cidade = dados['cidade']
    obra.estado = dados['estado']
    obra.status = dados['status']
    obra.data_inicio = converter_data(dados['data_inicio'])
    obra.save()


@login_required
def listar_obras(request):
    busca = request.GET.get('busca', '').strip()
    status_filtro = request.GET.get('status', '').strip()

    obras = Obra.objects.select_related('cliente').annotate(horas=Sum('apontamentos__total_horas'))

    if busca:
        obras = obras.filter(
            Q(nome_obra__icontains=busca)
            | Q(cidade__icontains=busca)
            | Q(cliente__nome_fantasia__icontains=busca)
        )

    if status_filtro in dict(Obra.STATUS_CHOICES):
        obras = obras.filter(status=status_filtro)

    contexto = {
        'obras': paginar(request, obras),
        'busca': busca,
        'status_filtro': status_filtro,
        'status_choices': Obra.STATUS_CHOICES,
        'parametros': parametros_sem_pagina(request),
    }
    return render(request, 'sgcc/listar_obras.html', contexto)


@login_required
def detalhar_obra(request, id):
    obra = get_object_or_404(Obra.objects.select_related('cliente'), id=id)
    apontamentos = obra.apontamentos.select_related('maquina', 'usuario')
    resumo = apontamentos.aggregate(total=Sum('total_horas'), quantidade=Count('id'),
                                    maquinas=Count('maquina', distinct=True))
    return render(request, 'sgcc/detalhar_obra.html', {
        'obra': obra,
        'apontamentos': apontamentos[:15],
        'resumo': resumo,
    })


@login_required
def cadastrar_obra(request):
    if not request.user.tem_perfil(PERFIS_CADASTRO):
        return sem_permissao(request, 'listar_obras')

    # Permite abrir o formulário já preenchido a partir da tela "Consultar CEP"
    dados = {campo: request.GET.get(campo, '').strip() for campo in CAMPOS_OBRA}
    dados['status'] = dados['status'] or 'EM_ANDAMENTO'
    dados['data_inicio'] = dados['data_inicio'] or str(timezone.localdate())
    erros = {}

    if request.method == 'POST':
        dados = ler_dados_obra(request)
        erros = validar_obra(dados)

        if not erros:
            obra = Obra()
            salvar_campos_obra(obra, dados)
            messages.success(request, 'Obra cadastrada com sucesso.')
            return redirect('detalhar_obra', id=obra.id)

        messages.error(request, 'Corrija os campos destacados.')

    return render(request, 'sgcc/form_obra.html', contexto_form_obra(dados, erros, 'Nova obra'))


@login_required
def editar_obra(request, id):
    obra = get_object_or_404(Obra, id=id)
    if not request.user.tem_perfil(PERFIS_CADASTRO):
        return sem_permissao(request, 'listar_obras')

    dados = {campo: str(getattr(obra, campo)) for campo in CAMPOS_OBRA}
    erros = {}

    if request.method == 'POST':
        dados = ler_dados_obra(request)
        erros = validar_obra(dados)

        if not erros:
            salvar_campos_obra(obra, dados)
            messages.success(request, 'Obra atualizada com sucesso.')
            return redirect('detalhar_obra', id=obra.id)

        messages.error(request, 'Corrija os campos destacados.')

    return render(request, 'sgcc/form_obra.html', contexto_form_obra(dados, erros, 'Editar obra', obra))


@login_required
def deletar_obra(request, id):
    obra = get_object_or_404(Obra, id=id)
    if not request.user.tem_perfil(PERFIS_CADASTRO):
        return sem_permissao(request, 'listar_obras')

    if request.method == 'POST':
        try:
            obra.delete()
            messages.success(request, 'Obra excluída com sucesso.')
            return redirect('listar_obras')
        except ProtectedError:
            messages.error(request, 'Esta obra possui apontamentos registrados e não pode ser excluída. '
                                    'Altere o status para Concluída ou Pausada.')
            return redirect('detalhar_obra', id=obra.id)

    return render(request, 'sgcc/confirmar_deletar.html', {
        'tipo': 'obra',
        'nome': obra.nome_obra,
        'url_cancelar': reverse('detalhar_obra', args=[obra.id]),
    })


# =============================================================================
# 5. CRUD de Máquinas
# =============================================================================

CAMPOS_MAQUINA = ['prefixo', 'tipo', 'marca', 'modelo', 'horimetro_atual', 'status']


def ler_dados_maquina(request):
    return {campo: request.POST.get(campo, '').strip() for campo in CAMPOS_MAQUINA}


def validar_maquina(dados, maquina=None):
    erros = {}

    dados['prefixo'] = dados['prefixo'].upper()
    if not dados['prefixo']:
        erros['prefixo'] = 'Informe o prefixo da máquina (ex.: ESC-001).'
    elif len(dados['prefixo']) > 20:
        erros['prefixo'] = 'O prefixo deve ter no máximo 20 caracteres.'
    elif Maquina.objects.filter(prefixo=dados['prefixo']).exclude(id=maquina.id if maquina else None).exists():
        erros['prefixo'] = 'Já existe uma máquina com este prefixo.'

    for campo, rotulo in [('tipo', 'o tipo'), ('marca', 'a marca'), ('modelo', 'o modelo')]:
        if not dados[campo]:
            erros[campo] = f'Informe {rotulo}.'
        elif len(dados[campo]) > 50:
            erros[campo] = 'Máximo de 50 caracteres.'

    # O horímetro só é informado no cadastro; depois ele muda pelos apontamentos
    if maquina is None:
        if converter_decimal(dados['horimetro_atual']) is None:
            erros['horimetro_atual'] = 'Informe um horímetro válido (ex.: 1450,5).'

    # Em manutenção a máquina só sai desse status quando a ordem é concluída
    if maquina is not None and maquina.possui_manutencao_aberta():
        dados['status'] = 'MANUTENCAO'
    elif dados['status'] not in ['DISPONIVEL', 'EM_USO']:
        erros['status'] = 'Selecione Disponível ou Em uso. Para manutenção, abra uma ordem de serviço.'

    return erros


@login_required
def listar_maquinas(request):
    busca = request.GET.get('busca', '').strip()
    status_filtro = request.GET.get('status', '').strip()

    maquinas = Maquina.objects.all()

    if busca:
        maquinas = maquinas.filter(
            Q(prefixo__icontains=busca)
            | Q(tipo__icontains=busca)
            | Q(marca__icontains=busca)
            | Q(modelo__icontains=busca)
        )

    if status_filtro in dict(Maquina.STATUS_CHOICES):
        maquinas = maquinas.filter(status=status_filtro)

    contexto = {
        'maquinas': paginar(request, maquinas),
        'busca': busca,
        'status_filtro': status_filtro,
        'status_choices': Maquina.STATUS_CHOICES,
        'parametros': parametros_sem_pagina(request),
    }
    return render(request, 'sgcc/listar_maquinas.html', contexto)


@login_required
def detalhar_maquina(request, id):
    maquina = get_object_or_404(Maquina, id=id)
    apontamentos = maquina.apontamentos.select_related('obra', 'usuario')
    manutencoes = maquina.manutencoes.select_related('mecanico')
    resumo = apontamentos.aggregate(total=Sum('total_horas'), quantidade=Count('id'))
    return render(request, 'sgcc/detalhar_maquina.html', {
        'maquina': maquina,
        'apontamentos': apontamentos[:10],
        'manutencoes': manutencoes[:10],
        'resumo': resumo,
    })


@login_required
def cadastrar_maquina(request):
    if not request.user.tem_perfil(PERFIS_CADASTRO):
        return sem_permissao(request, 'listar_maquinas')

    dados = {'status': 'DISPONIVEL', 'horimetro_atual': '0.0'}
    erros = {}

    if request.method == 'POST':
        dados = ler_dados_maquina(request)
        erros = validar_maquina(dados)

        if not erros:
            maquina = Maquina.objects.create(
                prefixo=dados['prefixo'],
                tipo=dados['tipo'],
                marca=dados['marca'],
                modelo=dados['modelo'],
                horimetro_atual=converter_decimal(dados['horimetro_atual']),
                status=dados['status'],
            )
            messages.success(request, 'Máquina cadastrada com sucesso.')
            return redirect('detalhar_maquina', id=maquina.id)

        messages.error(request, 'Corrija os campos destacados.')

    return render(request, 'sgcc/form_maquina.html', {
        'dados': dados, 'erros': erros, 'titulo': 'Nova máquina',
    })


@login_required
def editar_maquina(request, id):
    maquina = get_object_or_404(Maquina, id=id)
    if not request.user.tem_perfil(PERFIS_CADASTRO):
        return sem_permissao(request, 'listar_maquinas')

    dados = {campo: str(getattr(maquina, campo)) for campo in CAMPOS_MAQUINA}
    erros = {}

    if request.method == 'POST':
        dados = ler_dados_maquina(request)
        dados['horimetro_atual'] = str(maquina.horimetro_atual)
        erros = validar_maquina(dados, maquina)

        if not erros:
            maquina.prefixo = dados['prefixo']
            maquina.tipo = dados['tipo']
            maquina.marca = dados['marca']
            maquina.modelo = dados['modelo']
            maquina.status = dados['status']
            maquina.save()
            messages.success(request, 'Máquina atualizada com sucesso.')
            return redirect('detalhar_maquina', id=maquina.id)

        messages.error(request, 'Corrija os campos destacados.')

    return render(request, 'sgcc/form_maquina.html', {
        'dados': dados, 'erros': erros, 'titulo': 'Editar máquina', 'maquina': maquina,
    })


@login_required
def deletar_maquina(request, id):
    maquina = get_object_or_404(Maquina, id=id)
    if not request.user.tem_perfil(PERFIS_CADASTRO):
        return sem_permissao(request, 'listar_maquinas')

    if request.method == 'POST':
        try:
            maquina.delete()
            messages.success(request, 'Máquina excluída com sucesso.')
            return redirect('listar_maquinas')
        except ProtectedError:
            messages.error(request, 'Esta máquina possui apontamentos ou manutenções no histórico '
                                    'e não pode ser excluída.')
            return redirect('detalhar_maquina', id=maquina.id)

    return render(request, 'sgcc/confirmar_deletar.html', {
        'tipo': 'máquina',
        'nome': str(maquina),
        'url_cancelar': reverse('detalhar_maquina', args=[maquina.id]),
    })


# =============================================================================
# 6. CRUD de Apontamentos de horas
# =============================================================================

def contexto_form_apontamento(dados, erros, titulo, apontamento=None):
    return {
        'dados': dados,
        'erros': erros,
        'titulo': titulo,
        'apontamento': apontamento,
        'obras': Obra.objects.filter(status='EM_ANDAMENTO').select_related('cliente'),
        'maquinas': Maquina.objects.exclude(status='MANUTENCAO'),
        'hoje': str(timezone.localdate()),
    }


@login_required
def listar_apontamentos(request):
    apontamentos, filtros = filtrar_apontamentos(request)
    total = apontamentos.aggregate(total=Sum('total_horas'))['total'] or 0

    contexto = {
        'apontamentos': paginar(request, apontamentos, 15),
        'filtros': filtros,
        'total_horas': total,
        'obras': Obra.objects.all(),
        'maquinas': Maquina.objects.all(),
        'parametros': parametros_sem_pagina(request),
    }
    return render(request, 'sgcc/listar_apontamentos.html', contexto)


@login_required
def detalhar_apontamento(request, id):
    apontamento = get_object_or_404(
        ApontamentoHoras.objects.select_related('obra', 'obra__cliente', 'maquina', 'usuario'), id=id
    )
    return render(request, 'sgcc/detalhar_apontamento.html', {
        'apontamento': apontamento,
        'pode_excluir': apontamento.e_ultimo_da_maquina(),
    })


@login_required
def cadastrar_apontamento(request):
    if not request.user.tem_perfil(PERFIS_APONTAMENTO):
        return sem_permissao(request, 'listar_apontamentos')

    dados = {'data_apontamento': str(timezone.localdate()), 'maquina_id': request.GET.get('maquina', '')}
    erros = {}

    if request.method == 'POST':
        dados = {
            'data_apontamento': request.POST.get('data_apontamento', '').strip(),
            'obra_id': request.POST.get('obra_id', '').strip(),
            'maquina_id': request.POST.get('maquina_id', '').strip(),
            'horimetro_final': request.POST.get('horimetro_final', '').strip(),
            'observacoes': request.POST.get('observacoes', '').strip(),
        }

        data = converter_data(dados['data_apontamento'])
        if not data:
            erros['data_apontamento'] = 'Informe uma data válida.'

        obra = None
        if dados['obra_id'].isdigit():
            obra = Obra.objects.filter(id=int(dados['obra_id'])).first()
        if obra is None:
            erros['obra'] = 'Selecione uma obra.'

        maquina = None
        if dados['maquina_id'].isdigit():
            maquina = Maquina.objects.filter(id=int(dados['maquina_id'])).first()
        if maquina is None:
            erros['maquina'] = 'Selecione uma máquina.'

        horimetro_final = converter_decimal(dados['horimetro_final'])
        if horimetro_final is None:
            erros['horimetro_final'] = 'Informe o horímetro final (ex.: 1458,0).'

        if len(dados['observacoes']) > 2000:
            erros['observacoes'] = 'As observações devem ter no máximo 2000 caracteres.'

        if not erros:
            try:
                apontamento = registrar_apontamento(
                    obra=obra,
                    maquina=maquina,
                    usuario=request.user,
                    data_apontamento=data,
                    horimetro_final=horimetro_final,
                    observacoes=dados['observacoes'],
                )
                messages.success(
                    request,
                    f'Apontamento salvo: {apontamento.total_horas} h. '
                    f'Horímetro da {maquina.prefixo} atualizado para {apontamento.horimetro_final}.'
                )
                return redirect('detalhar_apontamento', id=apontamento.id)
            except ValidationError as erro:
                erros = {campo: lista[0] for campo, lista in erro.message_dict.items()}

        messages.error(request, 'Corrija os campos destacados.')

    return render(request, 'sgcc/form_apontamento.html',
                  contexto_form_apontamento(dados, erros, 'Registrar apontamento diário'))


@login_required
def editar_apontamento(request, id):
    apontamento = get_object_or_404(ApontamentoHoras.objects.select_related('obra', 'maquina'), id=id)
    if not request.user.tem_perfil(PERFIS_APONTAMENTO):
        return sem_permissao(request, 'listar_apontamentos')

    # Somente data e observações podem ser corrigidas; os horímetros ficam travados
    dados = {
        'data_apontamento': str(apontamento.data_apontamento),
        'observacoes': apontamento.observacoes,
    }
    erros = {}

    if request.method == 'POST':
        dados = {
            'data_apontamento': request.POST.get('data_apontamento', '').strip(),
            'observacoes': request.POST.get('observacoes', '').strip(),
        }

        data = converter_data(dados['data_apontamento'])
        if not data:
            erros['data_apontamento'] = 'Informe uma data válida.'
        elif data > timezone.localdate():
            erros['data_apontamento'] = 'A data do apontamento não pode estar no futuro.'
        elif data < apontamento.obra.data_inicio:
            erros['data_apontamento'] = 'A data é anterior ao início da obra.'

        if len(dados['observacoes']) > 2000:
            erros['observacoes'] = 'As observações devem ter no máximo 2000 caracteres.'

        if not erros:
            apontamento.data_apontamento = data
            apontamento.observacoes = dados['observacoes']
            apontamento.save(update_fields=['data_apontamento', 'observacoes'])
            messages.success(request, 'Apontamento atualizado com sucesso.')
            return redirect('detalhar_apontamento', id=apontamento.id)

        messages.error(request, 'Corrija os campos destacados.')

    return render(request, 'sgcc/form_apontamento.html',
                  contexto_form_apontamento(dados, erros, 'Editar apontamento', apontamento))


@login_required
def deletar_apontamento(request, id):
    apontamento = get_object_or_404(ApontamentoHoras.objects.select_related('maquina', 'obra'), id=id)
    if not request.user.tem_perfil(PERFIS_SOMENTE_ADMIN):
        return sem_permissao(request, 'listar_apontamentos')

    if request.method == 'POST':
        try:
            excluir_apontamento(apontamento)
            messages.success(request, 'Apontamento excluído. O horímetro da máquina foi restaurado.')
            return redirect('listar_apontamentos')
        except ValidationError as erro:
            messages.error(request, erro.message_dict['apontamento'][0])
            return redirect('detalhar_apontamento', id=apontamento.id)

    return render(request, 'sgcc/confirmar_deletar.html', {
        'tipo': 'apontamento',
        'nome': str(apontamento),
        'aviso': 'O horímetro da máquina voltará para o valor inicial deste apontamento.',
        'url_cancelar': reverse('detalhar_apontamento', args=[apontamento.id]),
    })


# =============================================================================
# 7. CRUD de Manutenções
# =============================================================================

def mecanicos_disponiveis():
    return Usuario.objects.filter(is_active=True, perfil='MECANICO')


@login_required
def listar_manutencoes(request):
    busca = request.GET.get('busca', '').strip()
    status_filtro = request.GET.get('status', '').strip()

    manutencoes = Manutencao.objects.select_related('maquina', 'mecanico')

    if busca:
        manutencoes = manutencoes.filter(
            Q(maquina__prefixo__icontains=busca) | Q(descricao_defeito__icontains=busca)
        )

    if status_filtro in dict(Manutencao.STATUS_CHOICES):
        manutencoes = manutencoes.filter(status=status_filtro)

    contexto = {
        'manutencoes': paginar(request, manutencoes),
        'busca': busca,
        'status_filtro': status_filtro,
        'status_choices': Manutencao.STATUS_CHOICES,
        'parametros': parametros_sem_pagina(request),
    }
    return render(request, 'sgcc/listar_manutencoes.html', contexto)


@login_required
def detalhar_manutencao(request, id):
    manutencao = get_object_or_404(Manutencao.objects.select_related('maquina', 'mecanico'), id=id)
    return render(request, 'sgcc/detalhar_manutencao.html', {'manutencao': manutencao})


@login_required
def cadastrar_manutencao(request):
    if not request.user.tem_perfil(PERFIS_MANUTENCAO):
        return sem_permissao(request, 'listar_manutencoes')

    dados = {'tipo': 'CORRETIVA', 'maquina_id': request.GET.get('maquina', '')}
    erros = {}

    if request.method == 'POST':
        dados = {
            'maquina_id': request.POST.get('maquina_id', '').strip(),
            'tipo': request.POST.get('tipo', '').strip(),
            'descricao_defeito': request.POST.get('descricao_defeito', '').strip(),
            'mecanico_id': request.POST.get('mecanico_id', '').strip(),
        }

        maquina = None
        if dados['maquina_id'].isdigit():
            maquina = Maquina.objects.filter(id=int(dados['maquina_id'])).first()
        if maquina is None:
            erros['maquina'] = 'Selecione uma máquina.'

        if dados['tipo'] not in dict(Manutencao.TIPO_CHOICES):
            erros['tipo'] = 'Selecione o tipo de manutenção.'

        if not dados['descricao_defeito']:
            erros['descricao_defeito'] = 'Descreva o defeito ou a necessidade.'

        mecanico = None
        if dados['mecanico_id']:
            if dados['mecanico_id'].isdigit():
                mecanico = mecanicos_disponiveis().filter(id=int(dados['mecanico_id'])).first()
            if mecanico is None:
                erros['mecanico_id'] = 'Mecânico inválido.'

        if not erros:
            try:
                manutencao = abrir_manutencao(maquina, dados['tipo'], dados['descricao_defeito'], mecanico)
                messages.success(request, f'Ordem #{manutencao.id} aberta. A máquina {maquina.prefixo} '
                                          f'está agora em manutenção.')
                return redirect('detalhar_manutencao', id=manutencao.id)
            except ValidationError as erro:
                erros = {campo: lista[0] for campo, lista in erro.message_dict.items()}

        messages.error(request, 'Corrija os campos destacados.')

    return render(request, 'sgcc/form_manutencao.html', {
        'dados': dados,
        'erros': erros,
        'titulo': 'Abrir ordem de manutenção',
        'maquinas': Maquina.objects.exclude(status='MANUTENCAO'),
        'mecanicos': mecanicos_disponiveis(),
        'tipo_choices': Manutencao.TIPO_CHOICES,
        'status_choices': Manutencao.STATUS_CHOICES,
    })


@login_required
def editar_manutencao(request, id):
    manutencao = get_object_or_404(Manutencao.objects.select_related('maquina'), id=id)
    if not request.user.tem_perfil(PERFIS_MANUTENCAO):
        return sem_permissao(request, 'listar_manutencoes')

    if manutencao.status == 'CONCLUIDA':
        messages.warning(request, 'Esta ordem já foi concluída e não pode ser alterada.')
        return redirect('detalhar_manutencao', id=manutencao.id)

    dados = {
        'tipo': manutencao.tipo,
        'status': manutencao.status,
        'descricao_defeito': manutencao.descricao_defeito,
        'descricao_servico': manutencao.descricao_servico or '',
        'mecanico_id': str(manutencao.mecanico_id or ''),
    }
    erros = {}

    if request.method == 'POST':
        dados = {
            'tipo': request.POST.get('tipo', '').strip(),
            'status': request.POST.get('status', '').strip(),
            'descricao_defeito': request.POST.get('descricao_defeito', '').strip(),
            'descricao_servico': request.POST.get('descricao_servico', '').strip(),
            'mecanico_id': request.POST.get('mecanico_id', '').strip(),
        }

        if dados['tipo'] not in dict(Manutencao.TIPO_CHOICES):
            erros['tipo'] = 'Selecione o tipo de manutenção.'
        if dados['status'] not in dict(Manutencao.STATUS_CHOICES):
            erros['status'] = 'Selecione um status válido.'
        if not dados['descricao_defeito']:
            erros['descricao_defeito'] = 'Descreva o defeito ou a necessidade.'

        mecanico = None
        if dados['mecanico_id']:
            if dados['mecanico_id'].isdigit():
                mecanico = mecanicos_disponiveis().filter(id=int(dados['mecanico_id'])).first()
            if mecanico is None:
                erros['mecanico_id'] = 'Mecânico inválido.'

        if not erros:
            try:
                atualizar_manutencao(
                    manutencao,
                    status=dados['status'],
                    tipo=dados['tipo'],
                    descricao_defeito=dados['descricao_defeito'],
                    descricao_servico=dados['descricao_servico'],
                    mecanico=mecanico,
                )
                if dados['status'] == 'CONCLUIDA':
                    messages.success(request, 'Ordem concluída. A máquina voltou a ficar disponível.')
                else:
                    messages.success(request, 'Ordem de manutenção atualizada.')
                return redirect('detalhar_manutencao', id=manutencao.id)
            except ValidationError as erro:
                erros = {campo: lista[0] for campo, lista in erro.message_dict.items()}

        messages.error(request, 'Corrija os campos destacados.')

    return render(request, 'sgcc/form_manutencao.html', {
        'dados': dados,
        'erros': erros,
        'titulo': f'Editar ordem #{manutencao.id}',
        'manutencao': manutencao,
        'mecanicos': mecanicos_disponiveis(),
        'tipo_choices': Manutencao.TIPO_CHOICES,
        'status_choices': Manutencao.STATUS_CHOICES,
    })


@login_required
def deletar_manutencao(request, id):
    manutencao = get_object_or_404(Manutencao.objects.select_related('maquina'), id=id)
    if not request.user.tem_perfil(PERFIS_SOMENTE_ADMIN):
        return sem_permissao(request, 'listar_manutencoes')

    if request.method == 'POST':
        excluir_manutencao(manutencao)
        messages.success(request, 'Ordem de manutenção excluída.')
        return redirect('listar_manutencoes')

    return render(request, 'sgcc/confirmar_deletar.html', {
        'tipo': 'ordem de manutenção',
        'nome': str(manutencao),
        'aviso': 'Se a ordem estiver aberta, a máquina voltará para o status Disponível.',
        'url_cancelar': reverse('detalhar_manutencao', args=[manutencao.id]),
    })


# =============================================================================
# 8. Relatório consolidado de horas
# =============================================================================

@login_required
def relatorio_horas(request):
    apontamentos, filtros = filtrar_apontamentos(request)

    # Totais gerais do período
    totais = apontamentos.aggregate(
        soma_horas=Sum('total_horas'),
        quantidade=Count('id'),
        media_horas=Avg('total_horas'),
        obras=Count('obra', distinct=True),
        maquinas=Count('maquina', distinct=True),
    )
    total_geral = totais['soma_horas'] or 0

    # Horas agrupadas por obra
    por_obra = list(
        apontamentos.values('obra__id', 'obra__nome_obra', 'obra__cliente__nome_fantasia')
        .annotate(horas=Sum('total_horas'), quantidade=Count('id'), maquinas=Count('maquina', distinct=True))
        .order_by('-horas')
    )

    # Horas agrupadas por máquina
    por_maquina = list(
        apontamentos.values('maquina__id', 'maquina__prefixo', 'maquina__tipo')
        .annotate(horas=Sum('total_horas'), quantidade=Count('id'), obras=Count('obra', distinct=True))
        .order_by('-horas')
    )

    # Percentual de participação de cada linha no total
    for linha in por_obra + por_maquina:
        linha['percentual'] = round(float(linha['horas']) * 100 / float(total_geral), 1) if total_geral else 0

    # Situação da frota e das ordens de manutenção
    situacao_frota = Maquina.objects.values('status').annotate(quantidade=Count('id')).order_by('status')
    nomes_status_maquina = dict(Maquina.STATUS_CHOICES)
    for linha in situacao_frota:
        linha['nome'] = nomes_status_maquina.get(linha['status'], linha['status'])

    situacao_manutencoes = Manutencao.objects.values('status').annotate(quantidade=Count('id')).order_by('status')
    nomes_status_manut = dict(Manutencao.STATUS_CHOICES)
    for linha in situacao_manutencoes:
        linha['nome'] = nomes_status_manut.get(linha['status'], linha['status'])

    contexto = {
        'filtros': filtros,
        'totais': totais,
        'por_obra': por_obra,
        'por_maquina': por_maquina,
        'situacao_frota': situacao_frota,
        'situacao_manutencoes': situacao_manutencoes,
        'obras': Obra.objects.all(),
        'maquinas': Maquina.objects.all(),
        'gerado_em': timezone.localtime(),
        'parametros': parametros_sem_pagina(request),
    }
    return render(request, 'sgcc/relatorio_horas.html', contexto)


@login_required
def exportar_relatorio_csv(request):
    apontamentos, filtros = filtrar_apontamentos(request)

    resposta = HttpResponse(content_type='text/csv; charset=utf-8')
    nome_arquivo = f'relatorio_horas_{timezone.localdate():%Y%m%d}.csv'
    resposta['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
    resposta.write('﻿')  # BOM para o Excel reconhecer acentos

    escritor = csv.writer(resposta, delimiter=';')
    escritor.writerow(['Data', 'Obra', 'Cliente', 'Máquina', 'Horímetro inicial',
                       'Horímetro final', 'Total de horas', 'Registrado por'])

    for apontamento in apontamentos:
        escritor.writerow([
            apontamento.data_apontamento.strftime('%d/%m/%Y'),
            apontamento.obra.nome_obra,
            apontamento.obra.cliente.nome_fantasia,
            apontamento.maquina.prefixo,
            str(apontamento.horimetro_inicial).replace('.', ','),
            str(apontamento.horimetro_final).replace('.', ','),
            str(apontamento.total_horas).replace('.', ','),
            apontamento.usuario.username,
        ])

    return resposta


# =============================================================================
# 9. Consumo da API externa ViaCEP
# =============================================================================

@login_required
def consultar_cep(request):
    """Tela de consulta de CEP: mostra o endereço e permite iniciar uma obra com ele."""
    cep = request.GET.get('cep', '').strip()
    endereco = None
    erro = None

    if cep:
        endereco, erro = consultar_viacep(cep)

    obras_mesmo_cep = []
    if endereco:
        obras_mesmo_cep = Obra.objects.filter(cep=endereco['cep']).select_related('cliente')

    return render(request, 'sgcc/consultar_cep.html', {
        'cep': cep,
        'endereco': endereco,
        'erro': erro,
        'obras_mesmo_cep': obras_mesmo_cep,
    })


@login_required
@require_GET
def buscar_cep_json(request):
    """
    Usada pelo botão "Buscar CEP" do formulário de obra.
    A chamada ao ViaCEP é feita pelo servidor, que devolve só o necessário.
    """
    endereco, erro = consultar_viacep(request.GET.get('cep', ''))
    if endereco:
        return JsonResponse({'ok': True, 'endereco': endereco})

    codigo = 404 if erro == 'CEP não encontrado.' else 400 if 'dígitos' in erro or 'formato' in erro else 503
    return JsonResponse({'ok': False, 'erro': erro}, status=codigo)


# =============================================================================
# 10. API REST própria — ViewSets (Django REST Framework)
# =============================================================================

class PermissaoPorPerfil(permissions.BasePermission):
    """
    Consultas (GET) são liberadas para qualquer usuário autenticado.
    Inclusão/alteração usa a lista `perfis_escrita` do ViewSet e
    exclusão usa `perfis_exclusao`.
    """
    message = 'Seu perfil não tem permissão para esta operação.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'DELETE':
            perfis = getattr(view, 'perfis_exclusao', PERFIS_SOMENTE_ADMIN)
        else:
            perfis = getattr(view, 'perfis_escrita', PERFIS_SOMENTE_ADMIN)
        return request.user.tem_perfil(perfis)


class ExclusaoProtegidaMixin:
    """Devolve 409 Conflict quando o registro tem histórico vinculado."""

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'O registro possui dados vinculados e não pode ser excluído.'},
                status=status.HTTP_409_CONFLICT,
            )


@extend_schema_view(
    list=extend_schema(
        summary='Listar clientes',
        parameters=[OpenApiParameter('busca', str, description='Busca por razão social, nome fantasia ou CNPJ')],
    ),
    retrieve=extend_schema(summary='Detalhar cliente'),
    create=extend_schema(summary='Cadastrar cliente'),
    update=extend_schema(summary='Alterar cliente'),
    partial_update=extend_schema(summary='Alterar parcialmente cliente'),
    destroy=extend_schema(summary='Excluir cliente'),
)
class ClienteViewSet(ExclusaoProtegidaMixin, viewsets.ModelViewSet):
    serializer_class = ClienteSerializer
    permission_classes = [PermissaoPorPerfil]
    perfis_escrita = PERFIS_CADASTRO
    perfis_exclusao = PERFIS_CADASTRO

    def get_queryset(self):
        clientes = Cliente.objects.all()
        busca = self.request.query_params.get('busca', '').strip()
        if busca:
            filtro = Q(razao_social__icontains=busca) | Q(nome_fantasia__icontains=busca)
            digitos = somente_digitos(busca)
            if digitos:
                filtro = filtro | Q(cnpj__icontains=digitos)
            clientes = clientes.filter(filtro)
        return clientes


@extend_schema_view(
    list=extend_schema(
        summary='Listar obras',
        parameters=[
            OpenApiParameter('status', str, description='EM_ANDAMENTO, PAUSADA ou CONCLUIDA'),
            OpenApiParameter('cidade', str, description='Parte do nome da cidade'),
            OpenApiParameter('cliente', int, description='ID do cliente'),
        ],
    ),
    retrieve=extend_schema(summary='Detalhar obra'),
    create=extend_schema(summary='Cadastrar obra (endereço completado pelo ViaCEP quando faltar cidade/UF)'),
    update=extend_schema(summary='Alterar obra'),
    partial_update=extend_schema(summary='Alterar parcialmente obra'),
    destroy=extend_schema(summary='Excluir obra'),
)
class ObraViewSet(ExclusaoProtegidaMixin, viewsets.ModelViewSet):
    serializer_class = ObraSerializer
    permission_classes = [PermissaoPorPerfil]
    perfis_escrita = PERFIS_CADASTRO
    perfis_exclusao = PERFIS_CADASTRO

    def get_queryset(self):
        obras = Obra.objects.select_related('cliente')
        parametros = self.request.query_params

        status_filtro = parametros.get('status', '').strip().upper()
        if status_filtro:
            obras = obras.filter(status=status_filtro)

        cidade = parametros.get('cidade', '').strip()
        if cidade:
            obras = obras.filter(cidade__icontains=cidade)

        cliente = parametros.get('cliente', '').strip()
        if cliente.isdigit():
            obras = obras.filter(cliente_id=int(cliente))

        return obras


@extend_schema_view(
    list=extend_schema(
        summary='Listar máquinas',
        parameters=[
            OpenApiParameter('status', str, description='DISPONIVEL, EM_USO ou MANUTENCAO'),
            OpenApiParameter('tipo', str, description='Parte do tipo do equipamento (ex.: Escavadeira)'),
        ],
    ),
    retrieve=extend_schema(summary='Detalhar máquina'),
    create=extend_schema(summary='Cadastrar máquina'),
    update=extend_schema(summary='Alterar máquina'),
    partial_update=extend_schema(summary='Alterar parcialmente máquina'),
    destroy=extend_schema(summary='Excluir máquina'),
)
class MaquinaViewSet(ExclusaoProtegidaMixin, viewsets.ModelViewSet):
    serializer_class = MaquinaSerializer
    permission_classes = [PermissaoPorPerfil]
    perfis_escrita = PERFIS_CADASTRO
    perfis_exclusao = PERFIS_CADASTRO

    def get_queryset(self):
        maquinas = Maquina.objects.all()
        parametros = self.request.query_params

        status_filtro = parametros.get('status', '').strip().upper()
        if status_filtro:
            maquinas = maquinas.filter(status=status_filtro)

        tipo = parametros.get('tipo', '').strip()
        if tipo:
            maquinas = maquinas.filter(tipo__icontains=tipo)

        return maquinas


@extend_schema_view(
    list=extend_schema(
        summary='Listar apontamentos de horas',
        parameters=[
            OpenApiParameter('obra', int, description='ID da obra'),
            OpenApiParameter('maquina', int, description='ID da máquina'),
            OpenApiParameter('data_inicio', str, description='Data inicial (AAAA-MM-DD)'),
            OpenApiParameter('data_fim', str, description='Data final (AAAA-MM-DD)'),
        ],
    ),
    retrieve=extend_schema(summary='Detalhar apontamento'),
    create=extend_schema(summary='Registrar apontamento (atualiza o horímetro da máquina)'),
    update=extend_schema(summary='Alterar data/observações do apontamento'),
    partial_update=extend_schema(summary='Alterar parcialmente data/observações'),
    destroy=extend_schema(summary='Excluir o apontamento mais recente de uma máquina'),
)
class ApontamentoViewSet(viewsets.ModelViewSet):
    serializer_class = ApontamentoSerializer
    permission_classes = [PermissaoPorPerfil]
    perfis_escrita = PERFIS_APONTAMENTO
    perfis_exclusao = PERFIS_SOMENTE_ADMIN

    def get_queryset(self):
        apontamentos, filtros = filtrar_apontamentos(self.request)
        return apontamentos

    def perform_create(self, serializer):
        # O usuário vem da autenticação, nunca do corpo da requisição
        serializer.save(usuario=self.request.user)

    def destroy(self, request, *args, **kwargs):
        apontamento = self.get_object()
        try:
            excluir_apontamento(apontamento)
        except ValidationError as erro:
            return Response(erro.message_dict, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        summary='Listar ordens de manutenção',
        parameters=[
            OpenApiParameter('status', str, description='ABERTA, EM_ANDAMENTO ou CONCLUIDA'),
            OpenApiParameter('maquina', int, description='ID da máquina'),
        ],
    ),
    retrieve=extend_schema(summary='Detalhar ordem de manutenção'),
    create=extend_schema(summary='Abrir ordem (coloca a máquina em manutenção)'),
    update=extend_schema(summary='Alterar/concluir ordem'),
    partial_update=extend_schema(summary='Alterar/concluir ordem parcialmente'),
    destroy=extend_schema(summary='Excluir ordem de manutenção'),
)
class ManutencaoViewSet(viewsets.ModelViewSet):
    serializer_class = ManutencaoSerializer
    permission_classes = [PermissaoPorPerfil]
    perfis_escrita = PERFIS_MANUTENCAO
    perfis_exclusao = PERFIS_SOMENTE_ADMIN

    def get_queryset(self):
        manutencoes = Manutencao.objects.select_related('maquina', 'mecanico')
        parametros = self.request.query_params

        status_filtro = parametros.get('status', '').strip().upper()
        if status_filtro:
            manutencoes = manutencoes.filter(status=status_filtro)

        maquina = parametros.get('maquina', '').strip()
        if maquina.isdigit():
            manutencoes = manutencoes.filter(maquina_id=int(maquina))

        return manutencoes

    def destroy(self, request, *args, **kwargs):
        excluir_manutencao(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)