# Ás Terraplanagem — Gestão Operacional (Fase 2)

Aplicação Django com CRUD de clientes, obras, máquinas, apontamentos de horas e
ordens de manutenção; busca; relatório consolidado (impressão e CSV); API REST
própria com JWT; e consumo da API externa ViaCEP.

## Estrutura

```
ProjetoWeb/
├── manage.py
├── requirements.txt
├── build.sh                 # build para hospedagem (Render)
├── .env.example             # modelo das variáveis de ambiente (sem segredos)
├── projeto/                 # settings.py, urls.py, wsgi.py, asgi.py
├── terrasebritas/           # app principal
│   ├── models.py            # modelos + regras de negócio (horímetro, manutenção)
│   ├── validacoes.py        # CNPJ, CEP, decimais, datas
│   ├── viacep.py            # integração ViaCEP (timeout, falhas, cache)
│   ├── serializers.py       # serializers DRF
│   ├── views.py             # views em função + ViewSets da API
│   ├── urls.py              # rotas web e /api/v1/
│   ├── admin.py
│   └── management/commands/popular_dados.py
├── templates/
│   ├── base.html
│   └── sgcc/                # telas do sistema
└── static/                  # css/estilo.css e img/logo.svg
```

## Como rodar localmente (passo a passo para a apresentação)

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Criar o arquivo .env a partir do modelo
# Windows: copy .env.example .env      Linux/macOS: cp .env.example .env
# Gere a SECRET_KEY e cole no .env:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# No .env, deixe também DEBUG=True e defina SENHA_DEMO=<uma senha forte>

# 4. Criar e aplicar as migrações
python manage.py makemigrations terrasebritas
python manage.py migrate

# 5. Criar o superusuário (pede usuário, e-mail e senha)
python manage.py createsuperuser

# 6. (Opcional) Carregar dados fictícios de demonstração
python manage.py popular_dados

# 7. Subir o servidor
python manage.py runserver
```

Acesse http://127.0.0.1:8000 e entre com o superusuário.

> Importante: depois do passo 4, faça commit da pasta `terrasebritas/migrations/`.
> A hospedagem executa só `migrate`, não `makemigrations`.

### Contas de demonstração (após `popular_dados`)

| Usuário           | Perfil      | Pode                                          |
|-------------------|-------------|-----------------------------------------------|
| admin_demo        | ADMIN       | tudo, inclusive excluir apontamentos e OS     |
| engenheiro_demo   | ENGENHEIRO  | clientes, obras, máquinas e apontamentos      |
| apontador_demo    | APONTADOR   | registrar apontamentos; consultar o restante  |
| mecanico_demo     | MECANICO    | abrir, atualizar e concluir manutenções       |

A senha de todas é o valor de `SENHA_DEMO`.

## Rotas principais

| Tela                     | Rota                                  |
|--------------------------|---------------------------------------|
| Dashboard                | `/`                                   |
| Clientes                 | `/listar_clientes`                    |
| Obras                    | `/listar_obras`                       |
| Máquinas                 | `/listar_maquinas`                    |
| Apontamentos             | `/listar_apontamentos`                |
| Manutenções              | `/listar_manutencoes`                 |
| Relatório consolidado    | `/relatorio_horas` (+ `/exportar_relatorio_csv`) |
| Consulta ViaCEP          | `/consultar_cep`                      |
| Sobre                    | `/sobre`                              |
| Swagger / Redoc          | `/api/v1/docs/` · `/api/v1/redoc/`    |
| Admin                    | `/admin/`                             |

## Regras de negócio implementadas

- O horímetro inicial do apontamento é sempre o horímetro atual da máquina; o final precisa ser maior (máx. 24 h por apontamento).
- Ao salvar o apontamento, o horímetro da máquina é atualizado na mesma transação (`select_for_update`).
- Máquina em manutenção não recebe apontamento; obra precisa estar "Em andamento".
- Só o apontamento mais recente de uma máquina pode ser excluído (o horímetro volta ao valor inicial).
- Abrir uma OS coloca a máquina em manutenção; concluir exige o serviço realizado e libera a máquina.
- CNPJ validado pelos dígitos verificadores e único.
- Clientes, obras e máquinas com histórico vinculado não podem ser excluídos (`PROTECT`).

## API REST (`/api/v1/`)

Autenticação JWT:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/token/ \
     -H "Content-Type: application/json" \
     -d '{"username": "apontador_demo", "password": "SUA_SENHA"}'
# resposta: {"refresh": "...", "access": "..."}
```

| Recurso       | Endpoint                     | Filtros (GET)                                   |
|---------------|------------------------------|-------------------------------------------------|
| Clientes      | `/api/v1/clientes/`          | `busca`                                         |
| Obras         | `/api/v1/obras/`             | `status`, `cidade`, `cliente`                   |
| Máquinas      | `/api/v1/maquinas/`          | `status`, `tipo`                                |
| Apontamentos  | `/api/v1/apontamentos/`      | `obra`, `maquina`, `data_inicio`, `data_fim`    |
| Manutenções   | `/api/v1/manutencoes/`       | `status`, `maquina`                             |

Todos aceitam GET (lista paginada e detalhe `/{id}/`), POST, PUT, PATCH e DELETE,
conforme o perfil. Exemplo de apontamento:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/apontamentos/ \
     -H "Authorization: Bearer <access>" -H "Content-Type: application/json" \
     -d '{"obra_id": 1, "maquina_id": 1, "data_apontamento": "2026-11-09", "horimetro_final": 1300.0}'
```

Códigos: 200, 201, 204, 400 (validação), 401 (sem token), 403 (perfil sem permissão),
404, 409 (exclusão bloqueada por histórico), 429 (limite de requisições).

## Publicação (Render)

- Build command: `./build.sh` · Start command: `gunicorn projeto.wsgi:application`
- Variáveis no painel: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=seu-app.onrender.com`,
  `CSRF_TRUSTED_ORIGINS=https://seu-app.onrender.com`, `DATABASE_URL` (PostgreSQL), `SENHA_DEMO`.
- Com `DEBUG=False` o projeto ativa HTTPS obrigatório, cookies seguros e HSTS.

## Diferenças em relação à documentação da Fase 1 (registrar no repositório)

- Estilos com **Bootstrap 5** em vez de Tailwind CSS, mantendo a paleta, a tipografia Inter e a assinatura visual definidas nos protótipos.
- Um único app Django (`terrasebritas`) em vez de um app por entidade; nomes de tabela via `Meta.db_table`.
- Listas da API paginadas (`count`, `next`, `previous`, `results`).
- A informação climática citada nos protótipos não foi implementada nesta versão.
