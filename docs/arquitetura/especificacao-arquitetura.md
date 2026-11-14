# Documento de Arquitetura --- Gestão Ás Terraplanagem

## 1. Objetivo

Este documento apresenta a organização técnica prevista para o sistema
Gestão AS Terraplanagem. A ideia é explicar quais tecnologias serão
utilizadas, como as partes da aplicação se comunicam e qual é a
responsabilidade de cada componente.

A arquitetura descrita corresponde ao planejamento da aplicação. A
estrutura final poderá receber ajustes durante a implementação, desde
que as mudanças sejam registradas e não comprometam os requisitos
definidos.

## 2. Visão geral

O sistema será uma aplicação web desenvolvida com Python e Django. O
Django será responsável pela estrutura principal, pelo processamento das
requisições e pela comunicação com o banco de dados. O Django REST
Framework será utilizado para disponibilizar uma API em formato JSON.

A aplicação terá duas formas principais de apresentação dos dados:

-   páginas HTML renderizadas pelo Django, utilizando templates;
-   endpoints REST para operações que precisem trocar dados em JSON.

O banco PostgreSQL será responsável por armazenar os usuários, clientes,
obras, máquinas, apontamentos e manutenções. As integrações ViaCEP e
OpenWeatherMap serão chamadas quando o sistema precisar consultar
endereços ou informações climáticas.

## 3. Tecnologias previstas

  -----------------------------------------------------------------------
  Tecnologia                          Responsabilidade
  ----------------------------------- -----------------------------------
  Python 3.11+                        Linguagem principal

  Django                              Estrutura da aplicação web, rotas,
                                      autenticação e acesso aos dados

  Django REST Framework               Serialização e endpoints REST

  PostgreSQL 15+                      Banco de dados relacional

  Django Template Language            Renderização de páginas HTML no
                                      servidor

  Tailwind CSS                        Estilização das telas

  JWT                                 Autenticação das chamadas
                                      protegidas da API

  Nginx                               Proxy reverso, conexão SSL/TLS e
                                      entrega de arquivos estáticos

  Gunicorn                            Servidor WSGI para executar a
                                      aplicação Django

  Docker / Docker Compose             Padronização do ambiente de
                                      execução

  pytest / pytest-django              Testes automatizados previstos

  GitHub Actions                      Pipeline de integração e entrega
                                      contínua previsto para a Fase 2
  -----------------------------------------------------------------------

## 4. Padrão arquitetural: MVT e API REST

### 4.1 Model

Os Models representam os dados da aplicação e são mapeados para tabelas
do PostgreSQL. Também podem conter validações relacionadas aos
registros. Por exemplo, o modelo de apontamento precisa representar os
horímetros inicial e final e o total de horas.

As regras que protegem a consistência dos dados não devem depender
apenas do formulário visual. Elas precisam ser verificadas no servidor.

### 4.2 View e APIView

As Views recebem as requisições, verificam os dados recebidos, chamam as
operações necessárias e preparam a resposta. Nas páginas tradicionais do
Django, a resposta pode ser um template HTML. Na API, as views do Django
REST Framework retornam dados serializados em JSON.

A camada de controle deve evitar concentrar responsabilidades sem
relação entre si. As operações de cadastro, consulta e validação
precisam ser organizadas de forma que possam ser testadas.

### 4.3 Templates

Os templates são arquivos HTML renderizados pelo Django. A interface
será estilizada com Tailwind CSS e deverá funcionar em diferentes
tamanhos de tela.

As telas previstas incluem o painel operacional, os cadastros, a
consulta de máquinas, o formulário de apontamento e as páginas de
manutenção. Os formulários devem apresentar mensagens claras quando
houver erro de preenchimento ou falha em uma integração.

### 4.4 Serializers

Os serializers do Django REST Framework convertem objetos e dados do
Django para estruturas que podem ser enviadas em JSON. Também podem
validar os dados recebidos pela API antes de criar ou atualizar
registros.

Por exemplo, o serializer de apontamento deverá verificar os valores de
horímetro e retornar um erro de validação quando o valor final for menor
ou igual ao inicial.

## 5. Componentes e fluxo de requisição

O fluxo de implantação previsto é:

1.  O usuário acessa o sistema pelo navegador.
2.  A requisição chega ao Nginx.
3.  O Nginx encaminha as requisições dinâmicas ao Gunicorn.
4.  O Gunicorn executa a aplicação Django.
5.  O Django identifica a rota e encaminha a operação para a View ou
    APIView correspondente.
6.  A aplicação consulta ou altera dados por meio dos Models e do ORM do
    Django.
7.  Quando necessário, a aplicação consulta o PostgreSQL ou um serviço
    externo.
8.  O resultado é devolvido como HTML ou JSON.

### 5.1 Diagrama simplificado

``` mermaid
flowchart TD
    U[Usuário / Navegador] --> N[Nginx - Proxy reverso e SSL]
    N --> G[Gunicorn - WSGI]
    G --> D[Aplicação Django]
    D --> T[Templates HTML]
    D --> R[API REST - DRF]
    D --> M[Models e regras de negócio]
    M --> P[(PostgreSQL)]
    D --> V[Integração ViaCEP]
    D --> W[Integração OpenWeatherMap]
```

## 6. Responsabilidade dos componentes de infraestrutura

### 6.1 Nginx

O Nginx será responsável por receber as conexões externas, encaminhar
requisições dinâmicas e apoiar a configuração de SSL/TLS no ambiente de
implantação. Também poderá servir os arquivos estáticos e de mídia
conforme a configuração do projeto.

### 6.2 Gunicorn

O Gunicorn executará a aplicação Django por meio da interface WSGI. Ele
recebe as requisições encaminhadas pelo Nginx e permite que o código
Python processe as operações.

### 6.3 Django Core

O módulo `core` concentra as configurações globais, incluindo
configurações de ambiente, rotas principais, middlewares e parâmetros de
conexão. Segredos, como chaves de API, não devem ser colocados
diretamente no código versionado.

### 6.4 PostgreSQL

O PostgreSQL mantém os dados de forma persistente. As relações entre
clientes, obras, máquinas, apontamentos e manutenções devem ser
definidas por chaves estrangeiras e restrições adequadas.

### 6.5 Serviços externos

A aplicação consulta o ViaCEP para obter informações de endereço e a
OpenWeatherMap para consultar condições climáticas. Como esses serviços
dependem de rede e de disponibilidade externa, as falhas devem ser
tratadas pela aplicação.

## 7. Organização do código

A estrutura prevista no documento inicial é:

``` text
ProjetoWeb/
├── docs/
│   ├── arquitetura/
│   ├── api/
│   ├── casos_de_uso/
│   └── fase1_especificacao.md
├── src/
│   ├── core/
│   ├── apps/
│   │   ├── usuarios/
│   │   ├── clientes/
│   │   ├── obras/
│   │   ├── maquinas/
│   │   ├── apontamentos/
│   │   └── manutencao/
│   ├── static/
│   ├── templates/
│   └── manage.py
├── tests/
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── README.md
└── requirements.txt
```

Os diretórios `docs/`, `tests/`, `static/` e `templates/` têm funções
distintas. A documentação registra as decisões do projeto, os testes
verificam o comportamento, os arquivos estáticos armazenam recursos de
interface e os templates contêm as páginas renderizadas pelo servidor.

## 8. Segurança e controle de acesso

A aplicação deverá autenticar os usuários e aplicar permissões de acordo
com os perfis definidos: administrador, engenheiro, apontador e
mecânico.

Para a API, as rotas protegidas utilizarão o cabeçalho
`Authorization: Bearer <jwt_access_token>`. A ausência de um token
válido deve resultar em resposta de não autenticado. A autorização deve
ser verificada para cada operação, não apenas no menu da interface.

Outros cuidados previstos:

-   manter senhas por meio dos mecanismos seguros do Django, sem
    armazenar senhas em texto puro;
-   manter chaves de API e credenciais fora do repositório;
-   utilizar HTTPS no ambiente publicado;
-   validar os dados recebidos em formulários e endpoints;
-   evitar retornar informações internas desnecessárias em mensagens de
    erro;
-   restringir as permissões do banco e dos usuários da aplicação ao
    necessário para a execução.

## 9. Tratamento de falhas

Falhas de comunicação com serviços externos não devem derrubar o
restante do sistema. Se o ViaCEP não responder, o formulário deverá
permitir preenchimento manual do endereço. Se a OpenWeatherMap estiver
indisponível, o painel poderá apresentar a mensagem
`Informação climática indisponível no momento`.

Erros de validação, como horímetro final inválido, devem ser retornados
de forma compreensível ao usuário. Erros inesperados devem ser
registrados para análise, sem expor detalhes internos na interface.

## 10. Testes da arquitetura

A arquitetura deverá permitir testes em diferentes níveis:

-   **Testes unitários:** verificar cálculos e regras de negócio, como a
    diferença entre horímetros.
-   **Testes de integração:** verificar a comunicação entre Models,
    Views, serializers e banco.
-   **Testes de API:** verificar payloads, respostas HTTP e
    autenticação.
-   **Testes das integrações:** verificar resposta válida, timeout e
    indisponibilidade dos serviços externos.
-   **Testes de interface:** verificar se os formulários e mensagens
    funcionam nos tamanhos de tela previstos.

A meta definida no planejamento é atingir pelo menos 80% de cobertura de
testes antes de permitir a integração em produção.

## 11. Implantação e ambiente

A execução será preparada com Docker e Docker Compose para reduzir
diferenças entre ambientes. O README do repositório deverá documentar os
pré-requisitos e os comandos de inicialização, migração e criação do
superusuário.

Os comandos previstos no documento inicial incluem:

``` bash
docker-compose up -d --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

Esses comandos dependem de o `docker-compose.yml` estar configurado com
o serviço `web` e com os demais serviços necessários. A configuração
real deve ser conferida no repositório antes da execução.

## 12. Decisões que precisam ser confirmadas na implementação

Alguns detalhes ainda dependem da implementação e não devem ser
considerados concluídos apenas por estarem documentados:

-   configuração final dos serviços e portas no Docker Compose;
-   estratégia completa de permissões para cada endpoint;
-   forma definitiva de armazenar e renovar tokens JWT;
-   configuração de produção do Nginx e Gunicorn;
-   limite de horas utilizado para cada manutenção preventiva;
-   estratégia de logs, monitoramento e recuperação de falhas.
