"""
Serializers da API REST (Django REST Framework).

As validações seguem as mesmas regras dos formulários HTML, porque uma
requisição pode chegar direto na API sem passar pela interface.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    ApontamentoHoras,
    Cliente,
    Maquina,
    Manutencao,
    Obra,
    Usuario,
    abrir_manutencao,
    atualizar_manutencao,
    registrar_apontamento,
)
from .validacoes import ESTADOS_BRASIL, cnpj_valido, somente_digitos
from .viacep import consultar_viacep


def erro_django_para_drf(erro):
    """Converte o ValidationError do Django no formato de erro do DRF."""
    if hasattr(erro, 'message_dict'):
        return serializers.ValidationError(erro.message_dict)
    return serializers.ValidationError({'detail': erro.messages})


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
class ClienteSerializer(serializers.ModelSerializer):
    # max_length 18 para aceitar o CNPJ com pontuação; ele é gravado só com dígitos
    cnpj = serializers.CharField(max_length=18)

    class Meta:
        model = Cliente
        fields = ['id', 'razao_social', 'nome_fantasia', 'cnpj', 'telefone', 'email', 'criado_em']
        read_only_fields = ['id', 'criado_em']

    def validate_cnpj(self, valor):
        cnpj = somente_digitos(valor)
        if not cnpj_valido(cnpj):
            raise serializers.ValidationError('CNPJ inválido.')
        repetido = Cliente.objects.filter(cnpj=cnpj)
        if self.instance:
            repetido = repetido.exclude(id=self.instance.id)
        if repetido.exists():
            raise serializers.ValidationError('Já existe um cliente com este CNPJ.')
        return cnpj

    def validate_razao_social(self, valor):
        if not valor.strip():
            raise serializers.ValidationError('Informe a razão social.')
        return valor.strip()

    def validate_nome_fantasia(self, valor):
        if not valor.strip():
            raise serializers.ValidationError('Informe o nome fantasia.')
        return valor.strip()


class ClienteResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nome_fantasia']


# ---------------------------------------------------------------------------
# Obras
# ---------------------------------------------------------------------------
class ObraSerializer(serializers.ModelSerializer):
    cliente = ClienteResumoSerializer(read_only=True)
    cliente_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.all(), source='cliente', write_only=True,
    )
    cep = serializers.CharField(max_length=9)
    cidade = serializers.CharField(max_length=100, required=False, allow_blank=True)
    estado = serializers.CharField(max_length=2, required=False, allow_blank=True)

    class Meta:
        model = Obra
        fields = [
            'id', 'cliente', 'cliente_id', 'nome_obra', 'cep', 'logradouro', 'numero',
            'bairro', 'cidade', 'estado', 'status', 'data_inicio',
        ]
        read_only_fields = ['id']

    def validate_cep(self, valor):
        cep = somente_digitos(valor)
        if len(cep) != 8:
            raise serializers.ValidationError('O CEP deve conter 8 dígitos.')
        return cep

    def validate_nome_obra(self, valor):
        if not valor.strip():
            raise serializers.ValidationError('Informe o nome da obra.')
        return valor.strip()

    def validate(self, dados):
        cep = dados.get('cep')
        cidade = dados.get('cidade', self.instance.cidade if self.instance else '')
        estado = dados.get('estado', self.instance.estado if self.instance else '')

        # Completa o endereço pelo ViaCEP quando cidade/UF não foram enviados
        if cep and (not cidade or not estado):
            endereco, erro = consultar_viacep(cep)
            if endereco:
                for campo in ['logradouro', 'bairro', 'cidade', 'estado']:
                    if not dados.get(campo):
                        dados[campo] = endereco[campo]
            else:
                raise serializers.ValidationError({
                    'cep': f'{erro} Envie cidade e estado manualmente.'
                })

        estado = (dados.get('estado') or estado or '').upper()
        if estado not in ESTADOS_BRASIL:
            raise serializers.ValidationError({'estado': 'UF inválida.'})
        dados['estado'] = estado

        if not (dados.get('cidade') or cidade):
            raise serializers.ValidationError({'cidade': 'Informe a cidade.'})

        return dados


# ---------------------------------------------------------------------------
# Máquinas
# ---------------------------------------------------------------------------
class MaquinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Maquina
        fields = ['id', 'prefixo', 'tipo', 'marca', 'modelo', 'horimetro_atual', 'status']
        read_only_fields = ['id']

    def validate_prefixo(self, valor):
        prefixo = valor.strip().upper()
        if not prefixo:
            raise serializers.ValidationError('Informe o prefixo da máquina.')
        repetido = Maquina.objects.filter(prefixo=prefixo)
        if self.instance:
            repetido = repetido.exclude(id=self.instance.id)
        if repetido.exists():
            raise serializers.ValidationError('Já existe uma máquina com este prefixo.')
        return prefixo

    def validate_horimetro_atual(self, valor):
        if valor < 0:
            raise serializers.ValidationError('O horímetro não pode ser negativo.')
        if self.instance and valor != self.instance.horimetro_atual:
            raise serializers.ValidationError(
                'O horímetro só é alterado pelos apontamentos de horas.'
            )
        return valor

    def validate_status(self, valor):
        if valor == 'MANUTENCAO' and not (self.instance and self.instance.status == 'MANUTENCAO'):
            raise serializers.ValidationError(
                'Para colocar a máquina em manutenção, abra uma ordem de manutenção.'
            )
        if self.instance and self.instance.possui_manutencao_aberta() and valor != 'MANUTENCAO':
            raise serializers.ValidationError(
                'A máquina possui ordem de manutenção em aberto; conclua a ordem primeiro.'
            )
        return valor


# ---------------------------------------------------------------------------
# Apontamentos
# ---------------------------------------------------------------------------
class ApontamentoSerializer(serializers.ModelSerializer):
    obra_id = serializers.PrimaryKeyRelatedField(
        queryset=Obra.objects.all(), source='obra', write_only=True,
    )
    maquina_id = serializers.PrimaryKeyRelatedField(
        queryset=Maquina.objects.all(), source='maquina', write_only=True,
    )
    horimetro_inicial = serializers.DecimalField(
        max_digits=10, decimal_places=1, required=False,
        help_text='Opcional. Se enviado, deve ser igual ao horímetro atual da máquina.',
    )
    usuario_registro = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = ApontamentoHoras
        fields = [
            'id', 'obra', 'maquina', 'obra_id', 'maquina_id', 'data_apontamento',
            'horimetro_inicial', 'horimetro_final', 'total_horas', 'observacoes',
            'usuario_registro', 'criado_em',
        ]
        read_only_fields = ['id', 'obra', 'maquina', 'total_horas', 'usuario_registro', 'criado_em']

    def validate(self, dados):
        # Na alteração, só a data e as observações podem mudar
        if self.instance:
            for campo in ['obra', 'maquina', 'horimetro_inicial', 'horimetro_final']:
                if campo in dados and dados[campo] != getattr(self.instance, campo):
                    raise serializers.ValidationError({
                        campo: 'Este campo não pode ser alterado. Exclua o apontamento e registre novamente.'
                    })
        return dados

    def create(self, dados):
        try:
            return registrar_apontamento(
                obra=dados['obra'],
                maquina=dados['maquina'],
                usuario=dados['usuario'],
                data_apontamento=dados['data_apontamento'],
                horimetro_final=dados['horimetro_final'],
                observacoes=dados.get('observacoes', ''),
                horimetro_inicial=dados.get('horimetro_inicial'),
            )
        except DjangoValidationError as erro:
            raise erro_django_para_drf(erro)

    def update(self, instancia, dados):
        instancia.data_apontamento = dados.get('data_apontamento', instancia.data_apontamento)
        instancia.observacoes = dados.get('observacoes', instancia.observacoes)
        instancia.save(update_fields=['data_apontamento', 'observacoes'])
        return instancia


# ---------------------------------------------------------------------------
# Manutenções
# ---------------------------------------------------------------------------
class ManutencaoSerializer(serializers.ModelSerializer):
    maquina_id = serializers.PrimaryKeyRelatedField(
        queryset=Maquina.objects.all(), source='maquina', write_only=True,
    )
    maquina_prefixo = serializers.CharField(source='maquina.prefixo', read_only=True)
    mecanico_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(is_active=True), source='mecanico',
        write_only=True, required=False, allow_null=True,
    )
    mecanico_nome = serializers.CharField(source='mecanico.username', read_only=True, default=None)

    class Meta:
        model = Manutencao
        fields = [
            'id', 'maquina', 'maquina_id', 'maquina_prefixo', 'mecanico_id', 'mecanico_nome',
            'tipo', 'horimetro_registro', 'descricao_defeito', 'descricao_servico',
            'data_inicio', 'data_conclusao', 'status',
        ]
        read_only_fields = ['id', 'maquina', 'horimetro_registro', 'data_inicio', 'data_conclusao']

    def validate_descricao_defeito(self, valor):
        if not valor.strip():
            raise serializers.ValidationError('Descreva o defeito ou a necessidade de manutenção.')
        return valor.strip()

    def create(self, dados):
        try:
            return abrir_manutencao(
                maquina=dados['maquina'],
                tipo=dados['tipo'],
                descricao_defeito=dados['descricao_defeito'],
                mecanico=dados.get('mecanico'),
            )
        except DjangoValidationError as erro:
            raise erro_django_para_drf(erro)

    def update(self, instancia, dados):
        if 'maquina' in dados and dados['maquina'] != instancia.maquina:
            raise serializers.ValidationError({'maquina_id': 'A máquina da ordem não pode ser alterada.'})
        try:
            return atualizar_manutencao(
                instancia,
                status=dados.get('status', instancia.status),
                tipo=dados.get('tipo', instancia.tipo),
                descricao_defeito=dados.get('descricao_defeito', instancia.descricao_defeito),
                descricao_servico=dados.get('descricao_servico', instancia.descricao_servico),
                mecanico=dados.get('mecanico', instancia.mecanico),
            )
        except DjangoValidationError as erro:
            raise erro_django_para_drf(erro)
