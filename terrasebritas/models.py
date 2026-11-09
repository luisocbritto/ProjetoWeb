"""
Modelos do sistema Ás Terraplanagem — Gestão Operacional.

Segue o documento docs/banco-de-dados/modelo-de-dados:
Usuário, Cliente, Obra, Máquina, Apontamento de Horas e Manutenção.

As regras de negócio que alteram mais de uma tabela (apontamento atualiza
o horímetro da máquina; manutenção altera o status da máquina) ficam em
funções deste arquivo, para que a interface web e a API REST usem a mesma
lógica.
"""
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from .validacoes import formatar_cep, formatar_cnpj

# Perfis que podem executar cada tipo de operação
PERFIS_CADASTRO = ['ADMIN', 'ENGENHEIRO']
PERFIS_APONTAMENTO = ['ADMIN', 'ENGENHEIRO', 'APONTADOR']
PERFIS_MANUTENCAO = ['ADMIN', 'MECANICO']
PERFIS_SOMENTE_ADMIN = ['ADMIN']

# Limite de horas de um único apontamento diário
LIMITE_HORAS_APONTAMENTO = Decimal('24.0')


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
        nome = self.get_full_name()
        return nome if nome else self.username

    def tem_perfil(self, perfis):
        """Superusuário sempre pode; os demais dependem do perfil."""
        if self.is_superuser:
            return True
        return self.perfil in perfis


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

    @property
    def cnpj_formatado(self):
        return formatar_cnpj(self.cnpj)


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

    @property
    def cep_formatado(self):
        return formatar_cep(self.cep)

    @property
    def endereco_completo(self):
        partes = [self.logradouro, self.numero, self.bairro]
        texto = ', '.join([p for p in partes if p])
        if texto:
            return f'{texto} — {self.cidade}/{self.estado}'
        return f'{self.cidade}/{self.estado}'


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
        return f'{self.prefixo} - {self.tipo} {self.marca} {self.modelo}'

    def possui_manutencao_aberta(self):
        return self.manutencoes.filter(status__in=['ABERTA', 'EM_ANDAMENTO']).exists()


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
        return f'{self.maquina.prefixo} em {self.obra.nome_obra} ({self.data_apontamento:%d/%m/%Y})'

    def e_ultimo_da_maquina(self):
        """Indica se este é o apontamento mais recente da máquina."""
        return not ApontamentoHoras.objects.filter(maquina=self.maquina, id__gt=self.id).exists()


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
    mecanico = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name='manutencoes',
        null=True, blank=True,
    )
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
        return f'OS #{self.id} - {self.maquina.prefixo} ({self.get_status_display()})'

    @property
    def aberta(self):
        return self.status in ['ABERTA', 'EM_ANDAMENTO']


# ---------------------------------------------------------------------------
# Regras de negócio
# ---------------------------------------------------------------------------

def registrar_apontamento(obra, maquina, usuario, data_apontamento, horimetro_final,
                          observacoes='', horimetro_inicial=None):
    """
    Registra um apontamento de horas e atualiza o horímetro da máquina.

    - o horímetro inicial é sempre o horímetro atual da máquina;
    - o horímetro final precisa ser maior que o inicial;
    - a obra precisa estar em andamento e a máquina não pode estar em manutenção.

    Lança ValidationError (com dicionário campo -> mensagem) se algo estiver errado.
    """
    with transaction.atomic():
        # Bloqueia a linha da máquina para evitar dois apontamentos simultâneos
        maquina = Maquina.objects.select_for_update().get(pk=maquina.pk)
        erros = {}

        if obra.status != 'EM_ANDAMENTO':
            erros['obra'] = 'Só é possível registrar horas em obras com status "Em andamento".'

        if maquina.status == 'MANUTENCAO':
            erros['maquina'] = 'Esta máquina está em manutenção e não pode receber apontamentos.'

        inicial = maquina.horimetro_atual
        if horimetro_inicial is not None and horimetro_inicial != inicial:
            erros['horimetro_inicial'] = (
                f'O horímetro inicial deve ser igual ao horímetro atual da máquina ({inicial}).'
            )

        if horimetro_final <= inicial:
            erros['horimetro_final'] = 'O horímetro final deve ser maior que o horímetro inicial.'
        elif horimetro_final - inicial > LIMITE_HORAS_APONTAMENTO:
            erros['horimetro_final'] = (
                f'O total de horas não pode passar de {LIMITE_HORAS_APONTAMENTO} em um apontamento.'
            )

        if data_apontamento > timezone.localdate():
            erros['data_apontamento'] = 'A data do apontamento não pode estar no futuro.'
        elif data_apontamento < obra.data_inicio:
            erros['data_apontamento'] = 'A data do apontamento é anterior ao início da obra.'

        if erros:
            raise ValidationError(erros)

        apontamento = ApontamentoHoras.objects.create(
            obra=obra,
            maquina=maquina,
            usuario=usuario,
            data_apontamento=data_apontamento,
            horimetro_inicial=inicial,
            horimetro_final=horimetro_final,
            total_horas=horimetro_final - inicial,
            observacoes=observacoes,
        )

        maquina.horimetro_atual = horimetro_final
        maquina.save(update_fields=['horimetro_atual'])

    return apontamento


def excluir_apontamento(apontamento):
    """
    Exclui um apontamento. Para não quebrar a sequência do horímetro,
    só é permitido excluir o apontamento mais recente da máquina; nesse
    caso o horímetro da máquina volta para o valor inicial do apontamento.
    """
    with transaction.atomic():
        maquina = Maquina.objects.select_for_update().get(pk=apontamento.maquina_id)
        if not apontamento.e_ultimo_da_maquina():
            raise ValidationError({
                'apontamento': 'Só é possível excluir o apontamento mais recente desta máquina.'
            })
        if maquina.horimetro_atual == apontamento.horimetro_final:
            maquina.horimetro_atual = apontamento.horimetro_inicial
            maquina.save(update_fields=['horimetro_atual'])
        apontamento.delete()


def abrir_manutencao(maquina, tipo, descricao_defeito, mecanico=None):
    """Abre uma ordem de manutenção e coloca a máquina em manutenção."""
    with transaction.atomic():
        maquina = Maquina.objects.select_for_update().get(pk=maquina.pk)
        if maquina.possui_manutencao_aberta():
            raise ValidationError({
                'maquina': 'Esta máquina já possui uma ordem de manutenção em aberto.'
            })

        manutencao = Manutencao.objects.create(
            maquina=maquina,
            mecanico=mecanico,
            tipo=tipo,
            horimetro_registro=maquina.horimetro_atual,
            descricao_defeito=descricao_defeito,
            status='ABERTA',
        )

        maquina.status = 'MANUTENCAO'
        maquina.save(update_fields=['status'])

    return manutencao


def atualizar_manutencao(manutencao, status, tipo, descricao_defeito, descricao_servico, mecanico):
    """
    Atualiza uma ordem de manutenção. Ao concluir, exige a descrição do
    serviço, registra a data de conclusão e libera a máquina.
    """
    if manutencao.status == 'CONCLUIDA':
        raise ValidationError({'status': 'Uma ordem concluída não pode mais ser alterada.'})

    if status == 'CONCLUIDA' and not (descricao_servico or '').strip():
        raise ValidationError({'descricao_servico': 'Descreva o serviço realizado para concluir a ordem.'})

    with transaction.atomic():
        manutencao.status = status
        manutencao.tipo = tipo
        manutencao.descricao_defeito = descricao_defeito
        manutencao.descricao_servico = descricao_servico
        manutencao.mecanico = mecanico

        if status == 'CONCLUIDA':
            manutencao.data_conclusao = timezone.now()

        manutencao.save()

        if status == 'CONCLUIDA':
            maquina = Maquina.objects.select_for_update().get(pk=manutencao.maquina_id)
            if not maquina.possui_manutencao_aberta():
                maquina.status = 'DISPONIVEL'
                maquina.save(update_fields=['status'])

    return manutencao


def excluir_manutencao(manutencao):
    """Exclui a ordem; se ela estava aberta, devolve a máquina para Disponível."""
    with transaction.atomic():
        maquina = Maquina.objects.select_for_update().get(pk=manutencao.maquina_id)
        manutencao.delete()
        if maquina.status == 'MANUTENCAO' and not maquina.possui_manutencao_aberta():
            maquina.status = 'DISPONIVEL'
            maquina.save(update_fields=['status'])
