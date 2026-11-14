# Especificação de Casos de Uso --- Gestão AS Terraplanagem

## 1. Objetivo

Este documento descreve como os usuários devem interagir com o sistema
Gestão AS Terraplanagem nas operações principais. Os casos de uso ajudam
a transformar os requisitos em fluxos que podem ser implementados e
testados pela equipe.

Os fluxos descritos representam o comportamento esperado. Durante o
desenvolvimento, as telas e mensagens poderão ser ajustadas, desde que
as regras principais sejam mantidas.

## 2. Atores do sistema

  -----------------------------------------------------------------------
  Ator                                Responsabilidade
  ----------------------------------- -----------------------------------
  Usuário autenticado                 Acessar as funções permitidas pelo
                                      seu perfil

  Administrador                       Gerenciar usuários e permissões

  Engenheiro ou gerente               Cadastrar e acompanhar obras e
                                      consultar informações operacionais

  Apontador ou operador               Registrar o horímetro e as horas de
                                      uso das máquinas

  Mecânico ou chefe de manutenção     Abrir, atualizar e concluir ordens
                                      de serviço
  -----------------------------------------------------------------------

Um mesmo usuário pode ter responsabilidades diferentes conforme o perfil
cadastrado, mas o sistema deverá verificar as permissões antes de
executar cada operação.

## 3. Visão geral dos casos de uso

Os casos de uso principais definidos nesta fase são:

-   **UC01 --- Autenticação e autorização**
-   **UC02 --- Gestão de obras**
-   **UC03 --- Apontamento diário de horas**
-   **UC04 --- Gestão de manutenções da frota**

O sistema também precisa manter os cadastros de clientes e máquinas,
pois essas informações são utilizadas nos fluxos de obras, apontamentos
e manutenções.

## 4. UC01 --- Autenticação e autorização

### 4.1 Descrição

Permite que usuários cadastrados acessem o sistema com suas credenciais.
Depois da validação, o sistema libera apenas as operações
correspondentes ao perfil do usuário. Para acesso à API, está prevista a
utilização de tokens JWT.

### 4.2 Atores

Todos os usuários cadastrados e ativos.

### 4.3 Pré-condições

-   O usuário deve estar cadastrado no banco de dados.
-   A conta deve estar ativa.
-   O usuário deve informar as credenciais solicitadas.

### 4.4 Pós-condições

-   Em caso de sucesso, o usuário recebe uma sessão válida na aplicação
    web ou os tokens previstos para a API.
-   Em caso de falha, o acesso não é liberado e uma mensagem informa que
    as credenciais não foram aceitas.

### 4.5 Fluxo principal

1.  O usuário acessa a tela de login ou envia uma requisição para
    `POST /api/v1/token/`.
2.  Informa e-mail e senha.
3.  O sistema verifica as credenciais.
4.  O sistema verifica se a conta está ativa.
5.  Se os dados estiverem corretos, o sistema inicia a sessão ou gera os
    tokens JWT.
6.  Na aplicação web, o usuário é encaminhado para a área inicial
    adequada ao seu perfil.
7.  Nas requisições da API, o token é utilizado para autenticar as
    próximas chamadas.

### 4.6 Fluxos alternativos e exceções

**A1 --- Senha incorreta**

1.  O sistema não autentica o usuário.
2.  Exibe a mensagem `Credenciais inválidas`.
3.  A tentativa pode ser registrada para controle de falhas de
    autenticação.

**A2 --- Usuário inativo**

1.  O sistema identifica que a conta está desativada.
2.  O acesso é negado.
3.  O sistema informa que o usuário deve procurar o administrador.

**A3 --- Token ausente, inválido ou expirado**

1.  O usuário tenta acessar um recurso protegido da API.
2.  A API rejeita a requisição.
3.  Retorna `401 Unauthorized`.

**A4 --- Usuário sem permissão**

1.  O usuário está autenticado, mas tenta executar uma operação não
    permitida para seu perfil.
2.  O sistema bloqueia a operação.
3.  A resposta deve indicar que o acesso não está autorizado para aquela
    ação.

### 4.7 Regras de negócio

-   Apenas contas ativas podem autenticar.
-   A autenticação não deve conceder acesso irrestrito a todas as
    funções.
-   As permissões devem ser verificadas também no servidor, e não apenas
    pela exibição ou ocultação de botões na tela.
-   As credenciais e os tokens devem ser tratados de forma segura.

### 4.8 Cenários de teste

  Cenário                                 Resultado esperado
  --------------------------------------- ---------------------------------
  E-mail e senha válidos, conta ativa     Login concluído
  Senha incorreta                         Login negado e mensagem de erro
  Conta inativa                           Acesso bloqueado
  Token ausente em rota protegida         Resposta `401`
  Token inválido ou expirado              Requisição rejeitada
  Usuário sem permissão para a operação   Ação bloqueada

## 5. UC02 --- Gestão de obras

### 5.1 Descrição

Permite cadastrar, atualizar e consultar obras da empresa, relacionando
cada obra a um cliente. O cadastro inclui o endereço do canteiro e prevê
consulta automática de CEP pelo ViaCEP.

### 5.2 Atores

Engenheiro e gerente de operação. O administrador poderá ter acesso
conforme as permissões configuradas.

### 5.3 Pré-condições

-   O usuário deve estar autenticado e ter permissão para gerenciar
    obras.
-   O cliente contratante deve estar cadastrado.
-   Os campos obrigatórios do formulário devem ser informados.

### 5.4 Pós-condições

A obra é armazenada com os dados fornecidos e fica disponível para
consulta. Se a obra estiver ativa para operação, poderá ser selecionada
nos apontamentos.

### 5.5 Fluxo principal

1.  O usuário abre a área de obras.
2.  Seleciona a opção `Nova Obra`.
3.  O sistema apresenta o formulário de cadastro.
4.  O usuário informa o CEP do canteiro.
5.  O sistema consulta o ViaCEP.
6.  Quando o CEP é localizado, os campos de logradouro, bairro, cidade e
    UF são preenchidos.
7.  O usuário informa o nome da obra, número, complemento quando
    aplicável, data de início e cliente.
8.  O sistema valida os campos.
9.  O usuário confirma o cadastro.
10. O sistema salva a obra e apresenta a confirmação.

### 5.6 Fluxos alternativos e exceções

**A1 --- CEP não localizado**

1.  A consulta não retorna um endereço válido.
2.  O sistema informa que o CEP não foi encontrado.
3.  Os campos de endereço ficam disponíveis para preenchimento manual.

**A2 --- ViaCEP indisponível**

1.  A consulta falha por timeout ou indisponibilidade do serviço.
2.  O sistema apresenta uma mensagem explicando que não foi possível
    consultar o CEP.
3.  O usuário pode preencher o endereço manualmente e continuar o
    cadastro.

**A3 --- Cliente não selecionado**

1.  O usuário tenta salvar sem informar o cliente.
2.  O sistema destaca o campo obrigatório.
3.  O cadastro não é concluído até que a informação seja corrigida.

**A4 --- Dados inválidos**

1.  O sistema identifica campo obrigatório vazio ou formato incorreto.
2.  O formulário apresenta os erros.
3.  O usuário corrige os dados e tenta salvar novamente.

### 5.7 Regras de negócio

-   Uma obra deve estar relacionada a um cliente.
-   A consulta de CEP serve para facilitar o preenchimento, mas não deve
    impedir o cadastro manual quando o serviço estiver indisponível.
-   A obra deve possuir um estado de acompanhamento, como
    `EM_ANDAMENTO`, `CONCLUIDA` ou `PAUSADA`.
-   O sistema deverá evitar a exclusão de registros que já possuam
    apontamentos relacionados, conforme as restrições de integridade do
    banco.
-   Apenas usuários autorizados podem criar ou alterar obras.

### 5.8 Cenários de teste

  Cenário                       Resultado esperado
  ----------------------------- ---------------------------------------
  CEP válido e encontrado       Endereço preenchido automaticamente
  CEP não encontrado            Aviso e opção de preenchimento manual
  Serviço ViaCEP indisponível   Cadastro pode continuar manualmente
  Cadastro sem cliente          Validação impede salvar
  Dados obrigatórios corretos   Obra cadastrada
  Usuário sem permissão         Operação bloqueada

## 6. UC03 --- Apontamento diário de horas

### 6.1 Descrição

Permite registrar o uso de uma máquina em uma obra em uma data
específica. O sistema utiliza o horímetro atual como referência inicial,
recebe o valor final informado pelo apontador e calcula a diferença em
horas.

### 6.2 Atores

Apontador de campo, operador e engenheiro, conforme as permissões
atribuídas.

### 6.3 Pré-condições

-   O usuário deve estar autenticado e autorizado.
-   A obra deve estar cadastrada e disponível para apontamento.
-   A máquina deve estar cadastrada e apta para uso.
-   O horímetro atual da máquina deve estar registrado.

### 6.4 Pós-condições

-   O apontamento fica armazenado com obra, máquina, usuário e data.
-   O total de horas é calculado a partir dos valores de horímetro.
-   O horímetro atual da máquina é atualizado para o valor final
    validado.

### 6.5 Fluxo principal

1.  O apontador acessa a opção de novo apontamento.
2.  Seleciona a obra.
3.  Seleciona a máquina.
4.  O sistema consulta o horímetro atual e apresenta esse valor como
    horímetro inicial.
5.  O apontador informa o horímetro final observado no equipamento.
6.  O sistema calcula `horímetro final - horímetro inicial`.
7.  O usuário informa observações operacionais, quando necessário.
8.  O sistema verifica se o horímetro final é maior que o inicial.
9.  O sistema confirma que a máquina pode receber apontamento.
10. O registro é salvo e o horímetro atual da máquina é atualizado.
11. O sistema apresenta a confirmação do registro.

### 6.6 Fluxos alternativos e exceções

**A1 --- Horímetro final menor ou igual ao inicial**

1.  O usuário informa o valor final.
2.  O sistema identifica que o valor é menor ou igual ao inicial.
3.  O sistema não salva o apontamento.
4.  É apresentada uma mensagem informando que o horímetro final precisa
    ser maior que o inicial.

**A2 --- Máquina em manutenção**

1.  O usuário seleciona uma máquina com situação de manutenção.
2.  O sistema impede o registro normal de horas.
3.  O usuário deverá selecionar outro equipamento ou verificar a
    situação com a manutenção.

**A3 --- Obra ou máquina indisponível**

1.  O sistema verifica que a obra ou máquina não está apta para
    apontamento.
2.  A operação é bloqueada e o usuário recebe uma mensagem explicativa.

**A4 --- Falha na gravação**

1.  O sistema não consegue concluir o salvamento.
2.  O apontamento não deve ser apresentado como concluído.
3.  O usuário recebe uma mensagem para tentar novamente e evitar criar
    registros duplicados.

### 6.7 Regras de negócio

-   O horímetro final deve ser maior que o horímetro inicial.
-   O total de horas corresponde à diferença entre os dois valores.
-   O usuário responsável pelo registro deve ser identificado.
-   O apontamento deve estar vinculado a uma obra e a uma máquina.
-   A máquina em manutenção não deve receber apontamentos operacionais
    normais.
-   O horímetro atual deve ser atualizado somente depois da validação e
    gravação bem-sucedida.
-   Os valores devem manter uma casa decimal, conforme o modelo de dados
    previsto.

### 6.8 Exemplo de cálculo

Se o horímetro inicial for `1450.5` e o final for `1458.0`, o total
será:

`1458.0 - 1450.5 = 7.5 horas`

O exemplo ilustra a regra de cálculo e não representa um apontamento
real.

### 6.9 Cenários de teste

  -----------------------------------------------------------------------
  Cenário                             Resultado esperado
  ----------------------------------- -----------------------------------
  Horímetro final maior que o inicial Apontamento salvo com total
                                      calculado

  Horímetro final igual ao inicial    Salvamento bloqueado

  Horímetro final menor que o inicial Salvamento bloqueado

  Máquina em manutenção               Apontamento normal impedido

  Usuário não autenticado             Acesso negado

  Falha de gravação                   Sistema não confirma sucesso
  -----------------------------------------------------------------------

## 7. UC04 --- Gestão de manutenções da frota

### 7.1 Descrição

Permite registrar e acompanhar manutenções preventivas e corretivas das
máquinas. Cada ordem de serviço mantém informações sobre o equipamento,
o horímetro no momento do registro, o tipo de manutenção, a descrição do
problema e o serviço realizado.

### 7.2 Atores

Mecânico e chefe de manutenção.

### 7.3 Pré-condições

-   O usuário deve estar autenticado e ter permissão para gerenciar
    manutenções.
-   A máquina deve estar cadastrada.

### 7.4 Pós-condições

A ordem de serviço é armazenada e o estado da máquina é atualizado de
acordo com a situação da manutenção. Quando o serviço é concluído, a
ordem recebe a data de conclusão e o equipamento pode voltar a ficar
disponível.

### 7.5 Fluxo principal

1.  O mecânico abre a área de manutenção.
2.  Seleciona a opção para abrir uma ordem de serviço.
3.  Seleciona a máquina.
4.  O sistema registra o horímetro atual da máquina.
5.  O mecânico escolhe o tipo de manutenção: preventiva ou corretiva.
6.  Informa a descrição do defeito ou do serviço necessário.
7.  O sistema salva a ordem de serviço.
8.  A máquina passa para o estado `MANUTENCAO`, conforme a regra
    definida.
9.  Durante o atendimento, o mecânico pode atualizar o andamento e
    preencher a descrição do serviço realizado.
10. Ao terminar, informa a data de conclusão e finaliza a ordem.
11. O sistema atualiza o status da ordem para concluída e a máquina
    volta a ficar disponível, desde que não exista outra restrição.

### 7.6 Fluxos alternativos e exceções

**A1 --- Máquina não cadastrada**

1.  O usuário tenta selecionar um equipamento inexistente.
2.  O sistema não permite criar a ordem sem uma máquina válida.
3.  O usuário deve cadastrar o equipamento ou selecionar outro já
    cadastrado.

**A2 --- Ordem com dados incompletos**

1.  O usuário tenta salvar sem informar dados obrigatórios.
2.  O sistema destaca os campos pendentes.
3.  A ordem só é salva depois da correção.

**A3 --- Necessidade de manutenção preventiva**

1.  O horímetro alcança o limite configurado para revisão.
2.  O sistema deverá sinalizar a necessidade de manutenção e prever a
    criação de uma ordem pendente de agendamento.
3.  O responsável verifica a indicação e organiza o atendimento.

**A4 --- Conclusão da ordem**

1.  O mecânico registra os dados do serviço executado.
2.  O sistema verifica os campos necessários para concluir a ordem.
3.  A ordem é marcada como concluída e a situação da máquina é
    atualizada.

### 7.7 Regras de negócio

-   A ordem de serviço deve estar vinculada a uma máquina.
-   O horímetro do registro deve refletir o valor da máquina no momento
    da abertura.
-   O tipo deve ser `PREVENTIVA` ou `CORRETIVA`.
-   A ordem pode assumir os estados `ABERTA`, `EM_ANDAMENTO` e
    `CONCLUIDA`.
-   Uma máquina em manutenção não deve receber apontamentos operacionais
    normais.
-   A conclusão deve manter o histórico do atendimento.
-   A regra de alerta preventivo depende de um limite de horas
    configurado. O valor exato desse limite precisa ser definido pela
    operação.

### 7.8 Cenários de teste

  -----------------------------------------------------------------------
  Cenário                             Resultado esperado
  ----------------------------------- -----------------------------------
  Abertura de ordem com máquina       Ordem criada com horímetro
  válida                              registrado

  Tipo de manutenção não informado    Validação impede salvar

  Máquina colocada em manutenção      Situação atualizada

  Serviço concluído com dados válidos Ordem concluída

  Horímetro atinge limite configurado Sistema sinaliza necessidade de
                                      preventiva

  Máquina em manutenção recebe        Operação bloqueada
  tentativa de apontamento            
  -----------------------------------------------------------------------

## 8. Relação entre os casos de uso

Os casos de uso compartilham dados, a autenticação controla o acesso às
demais funções, a gestão de obras disponibiliza os locais de trabalho
para os apontamentos, os apontamentos atualizam o histórico de horas e o
horímetro da máquina, a manutenção utiliza o cadastro da máquina e
também interfere na sua disponibilidade.

Por isso, as regras de validação devem ser implementadas no servidor e
testadas mesmo quando a interface já realiza verificações. Isso reduz o
risco de dados incorretos serem gravados por meio de requisições diretas
à API.
