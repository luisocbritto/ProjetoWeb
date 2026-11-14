# Documento de Visão --- Gestão AS Terraplanagem

## 1. Apresentação

O Gestão AS Terraplanagem é um sistema web pensado para organizar
informações sobre obras, máquinas, apontamentos de horas e manutenções.
A proposta é reunir em um só lugar dados que hoje podem ficar espalhados
entre planilhas, formulários em papel e anotações.

A documentação desta fase descreve o problema que o sistema pretende
resolver, quem vai utilizá-lo, quais funções fazem parte do escopo e
quais pontos serão considerados na avaliação do projeto. A implementação
será feita com Python e Django, utilizando PostgreSQL para armazenar os
dados.

## 2. Contexto e problema

A empresa AS Terraplanagem trabalha com equipamentos pesados, como
escavadeiras, tratores de esteira, pás carregadeiras e
caminhões. Essas máquinas podem estar distribuídas entre
diferentes obras, o que exige acompanhamento das horas trabalhadas, da
disponibilidade dos equipamentos e das manutenções realizadas.

Quando essas informações são controladas manualmente, algumas
dificuldades aparecem e a consolidação das horas pode demorar, os dados
podem chegar incompletos e fica mais difícil identificar se uma máquina
está perto do período recomendado para manutenção, também tornando mais
trabalhoso comparar a utilização dos equipamentos entre as obras.

Os principais problemas identificados são:

-   atraso na consolidação das horas trabalhadas e na preparação dos
    relatórios;
-   risco de manutenção preventiva ser esquecida, aumentando a chance de
    paradas não planejadas;
-   dificuldade para acompanhar a disponibilidade da frota;
-   informações de clientes, obras e equipamentos distribuídas em
    controles diferentes;
-   pouca visibilidade sobre o andamento operacional.

## 3. Justificativa

A criação de uma aplicação web permite centralizar os registros e manter
um histórico consultável das atividades, com os dados organizados, os
responsáveis poderão conferir os apontamentos, consultar o horímetro das
máquinas e acompanhar as ordens de serviço.

O sistema também prevê o uso de serviços externos para facilitar o
cadastro dos endereços das obras e exibir informações climáticas. Esses
recursos não substituem a avaliação dos responsáveis pela operação, mas
podem ajudar no planejamento diário.

Como a aplicação será acessada em ambientes de trabalho variados, a
interface deverá se adaptar a computadores, tablets e smartphones. Isso
é importante principalmente para os usuários que registram informações
diretamente no canteiro.

## 4. Objetivos

### 4.1 Objetivo geral

Desenvolver um sistema web para apoiar o controle de frota, obras,
apontamentos de horímetro e manutenções da empresa AS Terraplanagem.

### 4.2 Objetivos específicos

-   Reduzir em 40% o tempo gasto para consolidar relatórios de horas
    trabalhadas por obra.
-   Contribuir para reduzir em 25% as paradas não programadas por meio
    de alertas de manutenção baseados no horímetro.
-   Centralizar o cadastro de clientes, contratos e canteiros de obra.
-   Manter o histórico de utilização e manutenção dos equipamentos.
-   Facilitar o preenchimento dos endereços por meio da consulta de CEP.
-   Disponibilizar informações operacionais organizadas para apoiar o
    acompanhamento das obras.

Esses percentuais são metas do projeto e deverão ser avaliados depois
que o sistema for utilizado em condições reais (eles não representam
resultados já alcançados).

## 5. Público-alvo e partes interessadas

  -----------------------------------------------------------------------
  Perfil                  Necessidades principais Uso esperado
  ----------------------- ----------------------- -----------------------
  Administrador           Controlar os acessos e  Gerenciar usuários e
                          manter os cadastros     consultar informações
                          principais              do sistema

  Engenheiro ou gerente   Acompanhar obras e      Cadastrar e atualizar
  de obra                 apontamentos            obras, consultar
                                                  registros e acompanhar
                                                  a operação

  Apontador ou operador   Registrar as horas de   Selecionar a obra e o
  de campo                uso das máquinas        equipamento, informar o
                                                  horímetro final e
                                                  registrar observações

  Mecânico ou chefe de    Registrar e acompanhar  Abrir manutenções,
  manutenção              ordens de serviço       informar serviços
                                                  realizados e concluir
                                                  atendimentos

  Diretoria               Consultar informações   Acompanhar indicadores
                          consolidadas            operacionais e
                                                  relatórios disponíveis
  -----------------------------------------------------------------------

As permissões deverão considerar o perfil de cada usuário. Nem todo
usuário precisa ter acesso às mesmas operações, principalmente quando se
trata de alterar cadastros ou gerenciar acessos.

## 6. Escopo do sistema

### 6.1 Funcionalidades previstas

O sistema deverá contemplar:

1.  Autenticação e controle de acesso por perfil.
2.  Cadastro e gestão de clientes.
3.  Cadastro e acompanhamento de obras.
4.  Cadastro de máquinas, incluindo tipo, marca, modelo, prefixo,
    horímetro e situação.
5.  Registro diário de horas por máquina e obra.
6.  Validação do horímetro inicial e final.
7.  Acompanhamento de manutenções preventivas e corretivas.
8.  Histórico técnico das manutenções.
9.  Consulta de endereço por meio da API ViaCEP.
10. Consulta de condições climáticas por meio da OpenWeatherMap.
11. Painel com informações operacionais, como frota disponível, máquinas
    em manutenção e obras em andamento.
12. API REST para permitir integração futura com outros sistemas ou
    aplicações.

### 6.2 Fora do escopo da Fase 1

Não fazem parte do escopo definido para esta fase:

-   controle completo de folha de pagamento dos operadores;
-   rastreamento de máquinas em tempo real por hardware IoT ou
    telemetria GPS;
-   faturamento bancário e emissão automática de nota fiscal eletrônica.

Essas funções poderão ser avaliadas em etapas futuras, mas não devem ser
tratadas como entregas desta fase.

## 7. Requisitos e restrições

### 7.1 Requisitos funcionais

-   **RF01 --- Autenticação:** permitir que usuários cadastrados entrem
    no sistema com suas credenciais.
-   **RF02 --- Perfis de acesso:** controlar as operações disponíveis de
    acordo com o perfil do usuário.
-   **RF03 --- Clientes:** permitir o cadastro e a consulta dos
    clientes.
-   **RF04 --- Obras:** permitir o cadastro e a atualização das
    informações das obras.
-   **RF05 --- Consulta de CEP:** preencher automaticamente os campos de
    endereço quando o serviço ViaCEP estiver disponível.
-   **RF06 --- Máquinas:** manter o cadastro e a situação operacional
    dos equipamentos.
-   **RF07 --- Apontamentos:** registrar as horas trabalhadas por
    máquina, obra e data.
-   **RF08 --- Validação de horímetro:** impedir o registro quando o
    horímetro final for menor ou igual ao inicial.
-   **RF09 --- Manutenção:** registrar manutenções preventivas e
    corretivas.
-   **RF10 --- Alertas:** sinalizar a necessidade de manutenção conforme
    o limite de horas configurado.
-   **RF11 --- Clima:** apresentar informações climáticas da obra quando
    o serviço externo estiver disponível.
-   **RF12 --- Painel:** apresentar um resumo dos principais indicadores
    operacionais.

### 7.2 Requisitos não funcionais e restrições

-   A aplicação será desenvolvida em Python com Django.
-   O banco de dados previsto é PostgreSQL.
-   A interface deverá ser responsiva para uso em computador, tablet e
    smartphone.
-   As rotas protegidas da API deverão exigir autenticação.
-   As integrações externas deverão tratar falhas sem impedir o acesso
    às demais funções.
-   O projeto deverá possuir testes automatizados para as regras
    principais.
-   O código e a documentação deverão ser mantidos no repositório
    GitHub.

## 8. Premissas e riscos

### 8.1 Premissas

A proposta considera que os apontadores terão acesso à internet móvel
pelo menos uma vez ao dia para acessar o sistema pelo navegador, considerando 
que os dados de clientes, obras e máquinas serão cadastrados
corretamente pelos responsáveis.

### 8.2 Riscos

  -----------------------------------------------------------------------
  Risco                   Possível impacto        Medida prevista
  ----------------------- ----------------------- -----------------------
  Baixa adesão dos        Apontamentos continuam  Interface simples e
  operadores              sendo feitos fora do    orientação aos usuários
                          sistema                 

  Falha nas APIs externas Endereço ou clima não é Permitir endereço
                          preenchido              manual e exibir aviso
                          automaticamente         de indisponibilidade do
                                                  clima

  Registro incorreto do   Histórico operacional   Validar os valores
  horímetro               inconsistente           antes de salvar

  Permissões inadequadas  Usuários acessam        Definir e testar os
                          operações que não       perfis de acesso
                          deveriam executar       

  Atraso na implementação Entregas da Fase 2      Organizar tarefas por
                          ficam comprometidas     prioridade e acompanhar
                                                  os marcos
  -----------------------------------------------------------------------

## 9. Critérios de sucesso

A avaliação inicial do projeto considera os seguintes critérios:

-   mais de 90% dos apontamentos realizados pelo processo definido nas
    primeiras quatro semanas de implantação;
-   100% dos registros de manutenção vinculados à máquina correspondente
    e ao horímetro registrado;
-   tempo de resposta da API de integração inferior a 300 ms em
    condições normais de uso.

Os critérios deverão ser medidos por testes e, quando houver implantação
real, pela observação do uso do sistema. O desempenho pode variar
conforme infraestrutura, rede e disponibilidade dos serviços externos.

## 10. Tecnologias previstas

  -----------------------------------------------------------------------
  Tecnologia ou serviço               Utilização
  ----------------------------------- -----------------------------------
  Python 3.11 ou superior             Linguagem principal

  Django                              Desenvolvimento da aplicação web

  Django REST Framework               Construção da API REST

  PostgreSQL 15 ou superior           Persistência dos dados

  Django Templates e Tailwind CSS     Construção e estilização das telas

  JWT                                 Autenticação das requisições da API

  Docker e Docker Compose             Preparação do ambiente de execução

  ViaCEP                              Consulta de endereço por CEP

  OpenWeatherMap                      Consulta de condições climáticas

  GitHub Actions                      Pipeline de integração e entrega
                                      contínua previsto para a Fase 2
  -----------------------------------------------------------------------

## 11. Limites desta documentação

Este documento registra a visão e os requisitos previstos para o
sistema. Ele não significa que todas as funcionalidades já estejam
implementadas. Os detalhes de comportamento estão no documento de casos
de uso, a organização técnica está no documento de arquitetura e os
campos de armazenamento estão no modelo de dados.

## 12. Considerações finais

O objetivo principal é substituir controles dispersos por registros mais
organizados e fáceis de consultar. A primeira versão deve priorizar as
funções essenciais: cadastro de clientes e obras, controle das máquinas,
apontamento de horas e acompanhamento das manutenções. Com essa base
funcionando, será possível testar o sistema, corrigir problemas e
avaliar melhorias para as próximas fases.
