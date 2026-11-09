"""
Funções de conversão e validação usadas pelas views (formulários HTML)
e pelos serializers (API REST). Ficam em um só lugar para que as duas
entradas do sistema sigam exatamente as mesmas regras.
"""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

HORIMETRO_MAXIMO = Decimal('99999999.9')  # limite do campo DECIMAL(10,1)
ESTADOS_BRASIL = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO',
]


def somente_digitos(texto):
    """Remove tudo o que não for número. Ex.: '74.000-000' -> '74000000'."""
    return re.sub(r'\D', '', texto or '')


def converter_decimal(texto):
    """
    Converte um texto como '1450,5' ou '1450.5' em Decimal com 1 casa.
    Devolve None quando o valor é inválido.
    """
    if texto is None:
        return None
    texto = str(texto).replace(',', '.').strip()
    if texto == '':
        return None
    try:
        valor = Decimal(texto)
        if not valor.is_finite():
            return None
        valor = valor.quantize(Decimal('0.1'))
    except (InvalidOperation, ValueError):
        return None
    if valor < 0 or valor > HORIMETRO_MAXIMO:
        return None
    return valor


def converter_data(texto):
    """Converte 'AAAA-MM-DD' em date. Devolve None quando inválido."""
    try:
        return datetime.strptime((texto or '').strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


def calcular_digitos_cnpj(base):
    """Recebe os 12 primeiros dígitos do CNPJ e devolve os 2 dígitos verificadores."""
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1

    soma = sum(int(base[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    base13 = base + str(digito1)
    soma = sum(int(base13[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    return str(digito1) + str(digito2)


def cnpj_valido(cnpj):
    """Valida um CNPJ (somente dígitos) conferindo os dígitos verificadores."""
    if len(cnpj) != 14 or not cnpj.isdigit():
        return False
    if cnpj == cnpj[0] * 14:
        return False
    return cnpj[12:] == calcular_digitos_cnpj(cnpj[:12])


def cpf_valido(cpf):
    """Valida um CPF (somente dígitos) conferindo os dígitos verificadores."""
    if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11
        if digito == 10:
            digito = 0
        if digito != int(cpf[tamanho]):
            return False
    return True


def email_valido(email):
    """Validação simples de formato de e-mail."""
    return re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email or '') is not None


def formatar_cnpj(cnpj):
    if len(cnpj) != 14:
        return cnpj
    return f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}'


def formatar_cep(cep):
    if len(cep) != 8:
        return cep
    return f'{cep[:5]}-{cep[5:]}'
