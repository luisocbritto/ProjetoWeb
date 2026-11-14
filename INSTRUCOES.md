# Ás Terraplanagem — Gestão Operacional (Fase 2)

Aplicação Django com 4 telas: login, relatório consolidado de horas, lista de
obras com busca e formulário de obra (cadastro/edição com ViaCEP). Os apontamentos
de horas são registrados pela API REST própria. Clientes, máquinas e usuários são
cadastrados no painel `/admin`.

## Como rodar (Mac/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# cria o .env com uma SECRET_KEY aleatória
python -c "from django.core.management.utils import get_random_secret_key as g; open('.env','w').write(f'SECRET_KEY={g()}\nDEBUG=True\n')"

python manage.py makemigrations terrasebritas
python manage.py migrate
python manage.py createsuperuser
python manage.py popular_dados     # dados de exemplo (opcional)
python manage.py runserver
```

Acesse http://127.0.0.1:8000 (no Windows, ative com `.venv\Scripts\activate`).

## Onde está cada requisito

| Requisito | Onde |
|---|---|
| Cadastro e manutenção (CRUD) | Obras: `listar_obras`, `form_obra`, `deletar_obra` em `views.py` |
| Busca | `listar_obras` (`__icontains`) |
| Relatório | `relatorio` (`aggregate`, `values` + `annotate`), página inicial |
| API REST própria | ViewSets em `views.py`, `serializers.py`, documentação em `/api/v1/docs/` |
| API externa | `buscar_cep` (ViaCEP, com `timeout` e `try/except`) |
| Identidade visual | `static/css/estilo.css` e `static/img/logo.svg` |
| Configuração por ambiente | `projeto/settings.py` + `.env` / `.env.example` |
| Estáticos em produção | WhiteNoise (`settings.py`) |

## API REST

| Recurso | Endpoint | Métodos |
|---|---|---|
| Token JWT | `/api/v1/token/` | POST |
| Obras | `/api/v1/obras/` | GET, POST, PUT, PATCH, DELETE |
| Máquinas | `/api/v1/maquinas/` | GET |
| Apontamentos | `/api/v1/apontamentos/` | GET, POST |

```bash
# 1. obter o token
curl -X POST http://127.0.0.1:8000/api/v1/token/ -H "Content-Type: application/json" \
     -d '{"username": "SEU_USUARIO", "password": "SUA_SENHA"}'

# 2. registrar um apontamento (o horímetro inicial e o total são calculados pelo sistema)
curl -X POST http://127.0.0.1:8000/api/v1/apontamentos/ \
     -H "Authorization: Bearer <access>" -H "Content-Type: application/json" \
     -d '{"obra": 1, "maquina": 1, "data_apontamento": "2026-11-12", "horimetro_final": 1300.0}'
```

Códigos: 200, 201, 204, 400 (dados inválidos ou horímetro menor), 401 (sem token),
404, 409 (obra com apontamentos não pode ser excluída).

## Publicação (Render)

- Build: `./build.sh` · Start: `gunicorn projeto.wsgi:application`
- Variáveis: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`
- Com `DEBUG=False` o projeto força HTTPS e cookies seguros.
