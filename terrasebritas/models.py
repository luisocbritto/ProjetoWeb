# =============================================================================
# models.py — cada classe vira uma tabela no banco (makemigrations/migrate).
# Segue o modelo de dados da Fase 1 (docs/banco-de-dados/modelo-de-dados).
# =============================================================================
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


# Usuário do sistema: herda login/senha do Django e acrescenta o perfil
class Usuario(AbstractUser):
    PERFIL_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('ENGENHEIRO', 'Engenheiro'),
        ('APONTADOR', 'Apontador'),
        ('MECANICO', 'Mecânico'),
    ]

    email = models.EmailField('e-mail', unique=True)
    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, default='APONTADOR')
    cpf = models.CharField('CPF', max_length=11, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'usuarios'
        ordering = ['username']
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'

    def __str__(self):
        return self.username


# Cliente: empresa que contrata a terraplanagem (cadastrado pelo /admin)
class Cliente(models.Model):
    razao_social = models.CharField('razão social', max_length=200)
    nome_fantasia = models.CharField('nome fantasia', max_length=200)
    cnpj = models.CharField('CNPJ', max_length=14, unique=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField('e-mail', blank=True)
    criado_em = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        db_table = 'clientes'
        ordering = ['nome_fantasia']
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'

    def __str__(self):
        return self.nome_fantasia


# Obra: pertence a um cliente (1:N). PROTECT impede excluir cliente que tem obras.
class Obra(models.Model):
    STATUS_CHOICES = [
        ('EM_ANDAMENTO', 'Em andamento'),
        ('PAUSADA', 'Pausada'),
        ('CONCLUIDA', 'Concluída'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='obras')
    nome_obra = models.CharField('nome da obra', max_length=150)
    cep = models.CharField('CEP', max_length=8)
    logradouro = models.CharField(max_length=200, blank=True)
    numero = models.CharField('número', max_length=20, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100)
    estado = models.CharField('UF', max_length=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='EM_ANDAMENTO')
    data_inicio = models.DateField('data de início')

    class Meta:
        db_table = 'obras'
        ordering = ['-data_inicio', 'nome_obra']
        verbose_name = 'obra'
        verbose_name_plural = 'obras'

    def __str__(self):
        return self.nome_obra


# Máquina da frota. O horímetro conta as horas de uso do equipamento.
class Maquina(models.Model):
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível'),
        ('EM_USO', 'Em uso'),
        ('MANUTENCAO', 'Em manutenção'),
    ]

    prefixo = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=50)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    horimetro_atual = models.DecimalField('horímetro atual', max_digits=10, decimal_places=1, default=Decimal('0.0'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DISPONIVEL')

    class Meta:
        db_table = 'maquinas'
        ordering = ['prefixo']
        verbose_name = 'máquina'
        verbose_name_plural = 'máquinas'

    def __str__(self):
        return f'{self.prefixo} - {self.tipo}'


# Apontamento: horas de uma máquina em uma obra num dia.
# total_horas = horimetro_final - horimetro_inicial
class ApontamentoHoras(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.PROTECT, related_name='apontamentos')
    maquina = models.ForeignKey(Maquina, on_delete=models.PROTECT, related_name='apontamentos')
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='apontamentos')
    data_apontamento = models.DateField('data do apontamento')
    horimetro_inicial = models.DecimalField('horímetro inicial', max_digits=10, decimal_places=1)
    horimetro_final = models.DecimalField('horímetro final', max_digits=10, decimal_places=1)
    total_horas = models.DecimalField('total de horas', max_digits=10, decimal_places=1)
    observacoes = models.TextField('observações', blank=True)
    criado_em = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        db_table = 'apontamentos_horas'
        ordering = ['-data_apontamento', '-id']
        verbose_name = 'apontamento de horas'
        verbose_name_plural = 'apontamentos de horas'

    def __str__(self):
        return f'{self.maquina.prefixo} - {self.data_apontamento}'


# Ordem de manutenção de uma máquina (gerenciada pelo /admin)
class Manutencao(models.Model):
    TIPO_CHOICES = [
        ('PREVENTIVA', 'Preventiva'),
        ('CORRETIVA', 'Corretiva'),
    ]
    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('EM_ANDAMENTO', 'Em andamento'),
        ('CONCLUIDA', 'Concluída'),
    ]

    maquina = models.ForeignKey(Maquina, on_delete=models.PROTECT, related_name='manutencoes')
    mecanico = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='manutencoes',
                                 null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    horimetro_registro = models.DecimalField('horímetro no registro', max_digits=10, decimal_places=1)
    descricao_defeito = models.TextField('descrição do defeito')
    descricao_servico = models.TextField('serviço realizado', null=True, blank=True)
    data_inicio = models.DateTimeField('início', default=timezone.now)
    data_conclusao = models.DateTimeField('conclusão', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTA')

    class Meta:
        db_table = 'manutencoes'
        ordering = ['-data_inicio']
        verbose_name = 'manutenção'
        verbose_name_plural = 'manutenções'

    def __str__(self):
        return f'OS #{self.id} - {self.maquina.prefixo}'


# =============================================================================
# REGRA DE NEGÓCIO PRINCIPAL — usada pela tela (views) e pela API (serializers)
# =============================================================================
def registrar_apontamento(obra, maquina, usuario, data_apontamento, horimetro_final, observacoes=''):
    # Se algo der errado no meio, transaction.atomic desfaz tudo
    with transaction.atomic():
        inicial = maquina.horimetro_atual  # o inicial é sempre o horímetro atual da máquina

        erros = {}
        if maquina.status == 'MANUTENCAO':
            erros['maquina'] = 'Esta máquina está em manutenção.'
        if horimetro_final <= inicial:
            erros['horimetro_final'] = f'O horímetro final deve ser maior que {inicial}.'
        if erros:
            raise ValidationError(erros)  # a view/serializer mostra esses erros

        apontamento = ApontamentoHoras.objects.create(
            obra=obra, maquina=maquina, usuario=usuario,
            data_apontamento=data_apontamento,
            horimetro_inicial=inicial,
            horimetro_final=horimetro_final,
            total_horas=horimetro_final - inicial,
            observacoes=observacoes,
        )

        # Atualiza o horímetro da máquina para o próximo apontamento
        maquina.horimetro_atual = horimetro_final
        maquina.save()

    return apontamento
