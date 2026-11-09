"""
Integração com a API externa ViaCEP (https://viacep.com.br).

Usada no cadastro de obras para preencher logradouro, bairro, cidade e UF
a partir do CEP. A API é pública e não exige chave de acesso.

Tratamentos previstos no plano de integração:
- timeout configurável (VIACEP_TIMEOUT, padrão 5 segundos);
- falha de conexão e erros HTTP;
- resposta que não é JSON válido;
- CEP inexistente ({"erro": true});
- limite de requisições (HTTP 429);
- cache de 24 h para não consultar o mesmo CEP repetidas vezes.

Se a consulta falhar, o usuário pode preencher o endereço manualmente.
"""
import logging

import requests
from django.conf import settings
from django.core.cache import cache

from .validacoes import somente_digitos

logger = logging.getLogger(__name__)

TEMPO_CACHE = 60 * 60 * 24  # 24 horas


def consultar_viacep(cep):
    """
    Consulta um CEP no ViaCEP.

    Retorna uma tupla (endereco, erro):
    - endereco: dicionário com cep, logradouro, bairro, cidade e estado (ou None);
    - erro: mensagem amigável para o usuário (ou None quando deu certo).
    """
    cep = somente_digitos(cep)
    if len(cep) != 8:
        return None, 'Informe um CEP com 8 dígitos.'

    chave_cache = 'viacep_' + cep
    endereco = cache.get(chave_cache)
    if endereco:
        return endereco, None

    url = settings.VIACEP_URL.format(cep=cep)

    try:
        resposta = requests.get(url, timeout=settings.VIACEP_TIMEOUT)
    except requests.exceptions.Timeout:
        logger.warning('ViaCEP: tempo esgotado ao consultar o CEP %s', cep)
        return None, 'O ViaCEP demorou para responder. Tente novamente ou preencha o endereço manualmente.'
    except requests.exceptions.ConnectionError:
        logger.warning('ViaCEP: falha de conexão ao consultar o CEP %s', cep)
        return None, 'Não foi possível conectar ao ViaCEP. Verifique a internet ou preencha o endereço manualmente.'
    except requests.exceptions.RequestException:
        logger.exception('ViaCEP: erro inesperado ao consultar o CEP %s', cep)
        return None, 'Ocorreu um erro ao consultar o CEP. Preencha o endereço manualmente.'

    if resposta.status_code == 429:
        return None, 'Limite de consultas ao ViaCEP atingido. Aguarde alguns minutos ou preencha o endereço manualmente.'
    if resposta.status_code == 400:
        return None, 'CEP em formato inválido.'
    if resposta.status_code != 200:
        logger.warning('ViaCEP: status HTTP %s para o CEP %s', resposta.status_code, cep)
        return None, 'O ViaCEP está indisponível no momento. Preencha o endereço manualmente.'

    try:
        dados = resposta.json()
    except ValueError:
        logger.warning('ViaCEP: resposta não é JSON válido para o CEP %s', cep)
        return None, 'O ViaCEP retornou uma resposta inválida. Preencha o endereço manualmente.'

    if not isinstance(dados, dict) or dados.get('erro'):
        return None, 'CEP não encontrado.'

    endereco = {
        'cep': cep,
        'logradouro': (dados.get('logradouro') or '')[:200],
        'bairro': (dados.get('bairro') or '')[:100],
        'cidade': (dados.get('localidade') or '')[:100],
        'estado': (dados.get('uf') or '')[:2].upper(),
    }

    cache.set(chave_cache, endereco, TEMPO_CACHE)
    return endereco, None
