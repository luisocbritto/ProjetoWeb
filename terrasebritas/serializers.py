# =============================================================================
# serializers.py — convertem objetos do banco <-> JSON para a API REST
# =============================================================================
from django.core.exceptions import ValidationError
from rest_framework import serializers

from .models import ApontamentoHoras, Maquina, Obra, registrar_apontamento


class ObraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Obra
        fields = '__all__'  # todos os campos do model


class MaquinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Maquina
        fields = '__all__'


class ApontamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApontamentoHoras
        fields = '__all__'
        # Calculados pelo sistema: quem usa a API não envia esses campos
        read_only_fields = ['usuario', 'horimetro_inicial', 'total_horas']

    def create(self, dados):
        # Usa a mesma regra da tela; o usuário vem do token de login
        try:
            return registrar_apontamento(
                dados['obra'], dados['maquina'], self.context['request'].user,
                dados['data_apontamento'], dados['horimetro_final'], dados.get('observacoes', ''),
            )
        except ValidationError as erro:
            raise serializers.ValidationError(erro.message_dict)  # vira resposta 400
