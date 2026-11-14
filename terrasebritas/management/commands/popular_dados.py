# Cria dados fictícios para a demonstração: python manage.py popular_dados
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from terrasebritas.models import Cliente, Maquina, Obra, Usuario, registrar_apontamento


class Command(BaseCommand):
    help = 'Cria clientes, obras, máquinas e apontamentos de exemplo.'

    def handle(self, *args, **options):
        usuario = Usuario.objects.filter(is_superuser=True).first()
        if usuario is None:
            self.stdout.write('Crie antes um superusuário: python manage.py createsuperuser')
            return
        if Obra.objects.exists():
            self.stdout.write('Os dados de exemplo já existem.')
            return

        cliente1 = Cliente.objects.create(razao_social='Construtora Horizonte Ltda',
                                          nome_fantasia='Construtora Horizonte', cnpj='11222333000181')
        cliente2 = Cliente.objects.create(razao_social='Urbaniza Empreendimentos S.A.',
                                          nome_fantasia='Urbaniza', cnpj='11444777000161')

        inicio = date.today() - timedelta(days=30)
        obras = [
            Obra.objects.create(cliente=cliente1, nome_obra='Residencial Jardins', cep='74000000',
                                cidade='Goiânia', estado='GO', data_inicio=inicio),
            Obra.objects.create(cliente=cliente2, nome_obra='Loteamento Bela Vista', cep='75000000',
                                cidade='Anápolis', estado='GO', data_inicio=inicio),
        ]
        maquinas = [
            Maquina.objects.create(prefixo='ESC-001', tipo='Escavadeira', marca='Caterpillar',
                                   modelo='320', horimetro_atual=Decimal('1250.0')),
            Maquina.objects.create(prefixo='TRAT-002', tipo='Trator de Esteira', marca='Komatsu',
                                   modelo='D61', horimetro_atual=Decimal('890.0')),
            Maquina.objects.create(prefixo='CAMP-003', tipo='Caminhão Pipa', marca='Mercedes-Benz',
                                   modelo='Atego', horimetro_atual=Decimal('4120.0')),
        ]

        # 5 dias de apontamentos para cada máquina, usando a regra do sistema
        for dia in range(5, 0, -1):
            for i, maquina in enumerate(maquinas):
                registrar_apontamento(obras[i % 2], maquina, usuario, date.today() - timedelta(days=dia),
                                      maquina.horimetro_atual + Decimal('8.0'))

        self.stdout.write(self.style.SUCCESS('Dados de exemplo criados.'))
