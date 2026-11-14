# Gestão As Terraplanagem

Sistema web para gestão operacional de máquinas e obras de terraplanagem.

![Status](https://img.shields.io/badge/status-em_desenvolvimento-yellow)
![Versão](https://img.shields.io/badge/vers%C3%A3o-1.0.0-blue)
![Licença](https://img.shields.io/badge/licen%C3%A7a-acad%C3%AAmica-lightgrey)

## Informações do projeto

* **Instituição:** UniCEUB - Centro Universitário de Brasília
* **Curso:** Análise e Desenvolvimento de Sistemas
* **Disciplina:** Desenvolvimento Web (Python + Django)
* **Semestre:** 2026.2
* **Professor:** Felippe Pires Ferreira
* **Status:** Em desenvolvimento

---

## Sumário

1. [Descrição do projeto](#1-descrição-do-projeto)
2. [Objetivos](#2-objetivos)
3. [Funcionalidades](#3-funcionalidades)
4. [Demonstração](#4-demonstração)
5. [Tecnologias utilizadas](#5-tecnologias-utilizadas)
6. [Arquitetura](#6-arquitetura)
7. [Organização dos diretórios](#7-organização-dos-diretórios)
8. [Participantes](#8-participantes)
9. [Como executar](#9-como-executar)
10. [Configuração](#10-configuração)
11. [Testes](#11-testes)
12. [Uso de inteligência artificial](#12-uso-de-inteligência-artificial)
13. [Contribuição e fluxo de trabalho](#13-contribuição-e-fluxo-de-trabalho)
14. [Histórico de versões](#14-histórico-de-versões)
15. [Limitações e próximos passos](#15-limitações-e-próximos-passos)
16. [Licença e contato](#16-licença-e-contato)

---

## 1. Descrição do projeto

A gestão de serviços de terraplanagem envolve o acompanhamento de máquinas, horas trabalhadas, manutenções e obras. O controle dessas informações de forma manual pode dificultar o acompanhamento das atividades e gerar problemas no controle de horas e manutenções.

O **Gestão Ás Terraplanagem** é uma aplicação web desenvolvida em **Python e Django** para auxiliar no controle dessas informações.

O sistema permite registrar máquinas, obras, horas trabalhadas e ordens de serviço, além de disponibilizar informações de clima e endereço por meio de APIs externas.

A aplicação também possui uma API REST desenvolvida com **Django REST Framework (DRF)**.

### Objetivos

O objetivo principal é desenvolver uma aplicação para auxiliar no controle de máquinas e atividades realizadas em obras de terraplanagem.

Entre os principais objetivos estão:

* Registrar o horímetro inicial e final das máquinas.
* Controlar as horas trabalhadas em cada obra.
* Acompanhar manutenções preventivas e corretivas.
* Cadastrar clientes e obras.
* Buscar automaticamente dados de endereço através do CEP.
* Consultar informações climáticas dos locais das obras.
* Disponibilizar uma API REST para acesso aos dados.

### Público-alvo

O sistema foi pensado para os seguintes usuários:

* **Engenheiros e gerentes de obras:** acompanhamento das obras e equipamentos.
* **Apontadores e operadores:** registro das horas trabalhadas.
* **Mecânicos e responsáveis pela frota:** controle das ordens de serviço.
* **Clientes:** consulta de informações e relatórios relacionados às horas trabalhadas.

---

## 2. Funcionalidades

| Funcionalidade             | Descrição                                           | Status       |
| -------------------------- | --------------------------------------------------- | ------------ |
| Autenticação               | Login, logout e controle de usuários                | Implementada |
| Gestão de clientes e obras | Cadastro e gerenciamento de obras                   | Implementada |
| Gestão de frota            | Cadastro e acompanhamento das máquinas              | Implementada |
| Horímetro                  | Registro das horas iniciais e finais das máquinas   | Implementada |
| Ordens de serviço          | Registro de manutenções preventivas e corretivas    | Implementada |
| ViaCEP                     | Preenchimento automático de endereço através do CEP | Implementada |
| OpenWeatherMap             | Consulta das condições climáticas                   | Implementada |
| API REST                   | Endpoints para acesso aos dados do sistema          | Implementada |

### Requisitos não funcionais

* **Desempenho:** os endpoints da API devem responder em menos de 300 ms.
* **Segurança:** utilização de autenticação JWT e variáveis sensíveis armazenadas em `.env`.
* **Usabilidade:** interface responsiva para utilização em computadores e tablets.
* **Execução:** utilização de Docker para facilitar a configuração do ambiente.

---

## 3. Demonstração

As imagens utilizadas na documentação estão disponíveis no diretório `images/`.

| Tela               | Descrição                                         |
| ------------------ | ------------------------------------------------- |
| Dashboard          | Exibe informações gerais sobre a frota e as obras |
| Apontamento diário | Permite registrar o horímetro das máquinas        |
| Ordens de serviço  | Permite acompanhar as manutenções                 |

Repositório:

https://github.com/luis-britto/ProjetoWeb

---

## 4. Tecnologias utilizadas

| Categoria       | Tecnologia               |
| --------------- | ------------------------ |
| Linguagem       | Python 3.11+             |
| Backend         | Django                   |
| API             | Django REST Framework    |
| Frontend        | HTML5, CSS, JavaScript   |
| Banco de dados  | PostgreSQL / SQLite      |
| Testes          | pytest-django / unittest |
| Servidor        | Gunicorn                 |
| Proxy           | Nginx                    |
| Containerização | Docker / Docker Compose  |
| Versionamento   | Git / GitHub             |
| Testes de API   | Postman                  |
| APIs externas   | ViaCEP / OpenWeatherMap  |

---

## 5. Arquitetura

A aplicação utiliza o padrão **MVT (Model-View-Template)** do Django.

O Django é responsável pela aplicação web e o Django REST Framework é utilizado para disponibilizar os endpoints da API.

```text
Usuário
   |
   v
Nginx
   |
   v
Gunicorn
   |
   v
Aplicação Django
   |
   +-------------------+
   |                   |
   v                   v
PostgreSQL        APIs externas
                  |
                  +-- ViaCEP
                  |
                  +-- OpenWeatherMap
```

---

## 6. Organização dos diretórios

```text
.
├── README.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
│
├── docs/
│   ├── visao/
│   │   └── documento_de_visao.md
│   ├── casos-de-uso/
│   │   └── especificacao_casos_de_uso.md
│   ├── arquitetura/
│   │   └── arquitetura_aplicacao.md
│   ├── banco-de-dados/
│   │   └── modelo_relacional_der.md
│   ├── api/
│   │   ├── contrato_api_propria.md
│   │   └── plano_integracao_externa.md
│   ├── prototipos/
│   │   └── identidade_visual_e_prototipos.md
│   └── planejamento/
│       └── planejamento_fase2.md
│
├── images/
├── src/
└── tests/
```

### Principais arquivos e diretórios

| Arquivo / Diretório | Descrição                           |
| ------------------- | ----------------------------------- |
| `README.md`         | Documentação do projeto             |
| `.env.example`      | Exemplo das variáveis de ambiente   |
| `docs/`             | Documentação e materiais do projeto |
| `images/`           | Imagens utilizadas na documentação  |
| `src/`              | Código-fonte da aplicação           |
| `tests/`            | Testes automatizados                |

---

## 7. Participantes

| Nome                        | Matrícula | Função                                                        |
| --------------------------- | --------: | ------------------------------------------------------------- |
| João Lucas Trindade Diniz   |  22605421 | Coordenação, Backend, Modelagem de Dados, API REST e Testes   |
| Cauã Medeiros Alegre        |  22553411 | Backend, lógica de horímetro e manutenções                    |
| Luís Otávio Da Costa Britto |  22553336 | Frontend, Templates Django, integrações de API e documentação |

---

## 8. Como executar

### Pré-requisitos

* Git
* Python 3.11+
* Docker
* Docker Compose

Clonar o projeto

git clone https://github.com/luis-britto/ProjetoWeb.git

cd ProjetoWeb

Configurar o ambiente

Copie o arquivo .env.example:

cp .env.example .env

Depois, configure as variáveis necessárias no arquivo .env.

Executar com Docker
docker-compose up -d --build

Executar as migrações
docker-compose exec web python manage.py migrate

Criar usuário administrador
docker-compose exec web python manage.py createsuperuser

9. Configuração

As principais variáveis utilizadas pela aplicação são:

Variável	Obrigatória	Descrição
SECRET_KEY	Sim	Chave de segurança do Django
DEBUG	Sim	Define o modo de desenvolvimento
DATABASE_URL	Sim	URL de conexão com o banco
OPENWEATHER_API_KEY	Sim	Chave de acesso à API OpenWeatherMap

As credenciais reais não devem ser adicionadas ao repositório.

10. Testes

Para executar os testes:

docker-compose exec web pytest

Os testes são utilizados para verificar principalmente:

Validação do horímetro.
Métodos dos models.
Endpoints da API.
Autenticação JWT.
Integração com o ViaCEP.

Também são realizados testes manuais dos principais fluxos da aplicação.

11. Uso de inteligência artificial

Durante o desenvolvimento do projeto foram utilizadas ferramentas de inteligência artificial como apoio em algumas atividades.

Ferramentas utilizadas
ChatGPT
Google Gemini
Utilização

As ferramentas foram utilizadas principalmente para:

Revisão de textos;
Formatação de documentos Markdown;
Auxílio na elaboração inicial de alguns documentos;
Apoio na estruturação de contratos JSON da API.

As decisões relacionadas às regras de negócio, arquitetura, modelagem do banco de dados e implementação das principais funcionalidades foram realizadas pela equipe.

12. Contribuição e fluxo de trabalho

O projeto utiliza duas branches principais:

main
└── Versão estável

develop
└── Desenvolvimento e integração das funcionalidades

Os commits seguem o padrão:

feat: adiciona nova funcionalidade
fix: corrige problema
docs: atualiza documentação
13. Histórico de versões
Versão	Data	Descrição
1.0.0	04/10/2026	Entrega da Fase 1, documentação, arquitetura, modelo ER e endpoints da API
0.1.0	20/09/2026	Estrutura inicial do projeto
14. Limitações e próximos passos
Limitações atuais

Atualmente, algumas funcionalidades dependem de conexão com a internet, principalmente as consultas realizadas nas APIs externas.

Próximos passos

Implementar suporte offline para o aplicativo de campo.

Implementar exportação dos relatórios em PDF.

Implementar exportação dos relatórios em Excel.

15. Licença e contato
Licença

Projeto desenvolvido para fins acadêmicos no UniCEUB.

Documentação
Documento de Visão
Casos de Uso
Arquitetura
Modelo Relacional
Contrato da API
Contato

lucas.diniz19@sempreceub.com
Issues: GitHub Issues
