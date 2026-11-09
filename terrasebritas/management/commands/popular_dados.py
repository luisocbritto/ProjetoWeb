"""
Cria dados fictícios para demonstração e avaliação do sistema.

Uso:
    python manage.py popular_dados

A senha das contas de teste vem da variável de ambiente SENHA_DEMO
(definida no .env ou no painel da hospedagem). Nenhuma senha fica no código.
"""
import os
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from terrasebritas.models import (
    ApontamentoHoras,
    Cliente,
    Maquina,
    Obra,
    Usuario,
    abrir_manutencao,
    registrar_apontamento,
)
from terrasebritas.validacoes import calcular_digitos_cnpj


class Command(BaseCommand):
    help = 'Cria usuários de teste, clientes, obras, máquinas, apontamentos e manutenções fictícios.'

    def handle(self, *args, **options):
        senha = os.getenv('SENHA_DEMO')
        if not senha:
            raise CommandError('Defina a variável de ambiente SENHA_DEMO antes de executar este comando.')

        if Cliente.objects.exists():
            self.stdout.write(self.style.WARNING('Já existem dados cadastrados. Nada foi alterado.'))
            return

        # Usuários de teste, um por perfil
        usuarios = {}
        for username, perfil, nome in [
            ('admin_demo', 'ADMIN', 'Administrador'),
            ('engenheiro_demo', 'ENGENHEIRO', 'Engenheira Ana'),
            ('apontador_demo', 'APONTADOR', 'Apontador João'),
            ('mecanico_demo', 'MECANICO', 'Mecânico Carlos'),
        ]:
            usuario, criado = Usuario.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@exemplo.com', 'perfil': perfil, 'first_name': nome},
            )
            if criado:
                usuario.set_password(senha)
                usuario.save()
            usuarios[perfil] = usuario

        # Clientes com CNPJs fictícios (dígitos verificadores calculados)
        clientes = []
        for base, razao, fantasia in [
            ('112223330001', 'Construtora Horizonte Ltda', 'Construtora Horizonte'),
            ('445556660001', 'Urbaniza Empreendimentos S.A.', 'Urbaniza'),
            ('778889990001', 'Prefeitura Municipal de Exemplo', 'Prefeitura de Exemplo'),
        ]:
            clientes.append(Cliente.objects.create(
                razao_social=razao,
                nome_fantasia=fantasia,
                cnpj=base + calcular_digitos_cnpj(base),
                telefone='(62) 3000-0000',
                email='contato@exemplo.com',
            ))

        hoje = timezone.localdate()
        inicio = hoje - timedelta(days=40)

        obras = [
            Obra.objects.create(cliente=clientes[0], nome_obra='Terraplanagem Residencial Jardins',
                                cep='74000000', logradouro='Avenida Exemplo', numero='S/N',
                                bairro='Setor Central', cidade='Goiânia', estado='GO',
                                status='EM_ANDAMENTO', data_inicio=inicio),
            Obra.objects.create(cliente=clientes[1], nome_obra='Loteamento Bela Vista',
                                cep='75000000', logradouro='Rodovia Exemplo', numero='Km 12',
                                bairro='Zona Rural', cidade='Anápolis', estado='GO',
                                status='EM_ANDAMENTO', data_inicio=inicio),
            Obra.objects.create(cliente=clientes[2], nome_obra='Pavimentação Vias Rurais',
                                cep='75800000', logradouro='Estrada Vicinal', numero='S/N',
                                bairro='Zona Rural', cidade='Jataí', estado='GO',
                                status='PAUSADA', data_inicio=inicio),
        ]

        maquinas = [
            Maquina.objects.create(prefixo='ESC-001', tipo='Escavadeira Hidráulica', marca='Caterpillar',
                                   modelo='320', horimetro_atual=Decimal('1250.0')),
            Maquina.objects.create(prefixo='TRAT-002', tipo='Trator de Esteira', marca='Komatsu',
                                   modelo='D61', horimetro_atual=Decimal('890.2')),
            Maquina.objects.create(prefixo='MOTO-003', tipo='Motoniveladora', marca='John Deere',
                                   modelo='670G', horimetro_atual=Decimal('2310.5')),
            Maquina.objects.create(prefixo='CAMP-004', tipo='Caminhão Pipa', marca='Mercedes-Benz',
                                   modelo='Atego 2430', horimetro_atual=Decimal('4120.0')),
            Maquina.objects.create(prefixo='RET-005', tipo='Retroescavadeira', marca='JCB',
                                   modelo='3CX', horimetro_atual=Decimal('560.0')),
        ]

        # Apontamentos dos últimos 10 dias usando a mesma regra da tela
        horas_por_dia = [Decimal('8.5'), Decimal('6.8'), Decimal('7.5'), Decimal('9.0')]
        for dias_atras in range(10, 0, -1):
            data = hoje - timedelta(days=dias_atras)
            for indice, maquina in enumerate(maquinas[:4]):
                maquina.refresh_from_db()
                obra = obras[indice % 2]
                registrar_apontamento(
                    obra=obra,
                    maquina=maquina,
                    usuario=usuarios['APONTADOR'],
                    data_apontamento=data,
                    horimetro_final=maquina.horimetro_atual + horas_por_dia[indice],
                    observacoes='Registro gerado para demonstração.',
                )

        # Uma ordem de manutenção aberta
        abrir_manutencao(maquinas[4], 'CORRETIVA', 'Vazamento no cilindro hidráulico da caçamba.',
                         usuarios['MECANICO'])

        self.stdout.write(self.style.SUCCESS(
            f'Dados criados: {Cliente.objects.count()} clientes, {Obra.objects.count()} obras, '
            f'{Maquina.objects.count()} máquinas, {ApontamentoHoras.objects.count()} apontamentos.'
        ))
        self.stdout.write('Usuários de teste: admin_demo, engenheiro_demo, apontador_demo, mecanico_demo '
                          '(senha = valor de SENHA_DEMO).')
