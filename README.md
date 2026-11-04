# Repositorio-do-Projeto-SentinelaLog

# SentinelaLog

Monitor de acessos e detecção de anomalias para um laboratório de informática escolar, feito em Python e executado pelo terminal.

Projeto da disciplina **Fundamentos de Programação (2026-2, Turma B)**.

> **Aviso:** sistema didático. Usa apenas dados fictícios criados pelo grupo. Não serão usados dados reais de pessoas nem de sistemas da escola ou de terceiros.

## O problema

Alguém acessou a conta de um professor às 3h da manhã e apagou arquivos. A responsável pelo laboratório só descobriu dois dias depois e não tinha como saber quem foi, de onde veio, nem se aquilo já tinha acontecido antes.

O SentinelaLog registra os acessos, classifica cada um por nível de risco, explica o motivo da classificação e alerta antes que o estrago aconteça.

## Funcionalidades

- **Usuários:** cadastro, listagem, edição e exclusão, com perfil (estudante, professor, administrador) e horário permitido. Na listagem, a matrícula aparece mascarada (`20******`). Revelar uma matrícula exige informar o motivo e fica registrado no log.
- **Acessos:** registro com usuário, data e hora, máquina e resultado. Um acesso registrado não pode ser editado nem excluído.
- **Análise de risco:** cada acesso é classificado como normal, suspeito ou crítico, e o sistema mostra o porquê.
- **Lista de bloqueio:** o arquivo `maquinas_bloqueadas.txt` lista máquinas ou origens bloqueadas, e o sistema avisa quando um acesso vem de uma delas.
- **Detecção de risco:** alerta quando a mesma máquina é usada por mais de um usuário e mostra quais são.
- **Auditoria:** toda operação relevante vai para um log, com operador, operação, usuário afetado e data/hora. Consulta pelo menu.
- **Relatório de segurança:** total de acessos, falhas, usuários com mais falhas, horários mais movimentados (com gráfico em texto) e quantidade de acessos suspeitos e críticos.
- **Persistência:** tudo é salvo em `.csv` e `.txt` na pasta `dados/` e continua disponível entre execuções.
- **Reservado:** a opção 7 do menu está reservada para o módulo de IA que será integrado ao longo do semestre.

## Como executar

Requisito: Python 3, sem instalar nenhuma biblioteca.

```bash
python sentinelalog.py
```

Na primeira execução, a pasta `dados/` e os arquivos são criados automaticamente. O sistema pede o nome do operador, que é gravado no log de auditoria.

Para começar do zero, apague a pasta `dados/`.

## Critérios de classificação

Cada situação suspeita soma pontos. O total (máximo 100) define a classe:

| Situação | Pontos |
|---|---|
| Acesso com falha | +10 |
| Fora do horário permitido do usuário | +30 |
| Madrugada (00h às 05h59), além do ponto anterior | +20 |
| Professor ou administrador com sucesso fora do horário | +20 |
| Máquina na lista de bloqueio | +70 |
| Matrícula não cadastrada | +35 |
| Conta de usuário bloqueada voltou a ser usada | +40 |
| 3 ou mais falhas seguidas da mesma matrícula | +25 |
| Mesma matrícula em máquinas diferentes em até 5 minutos | +30 |

**Normal:** menos de 30 pontos. **Suspeito:** de 30 a 69. **Crítico:** 70 ou mais.

Por que esses critérios: horário, madrugada e perfil refletem o incidente original (conta de professor aberta de madrugada); falhas seguidas e matrícula desconhecida indicam tentativa de adivinhar acesso; troca rápida de máquina indica uso simultâneo ou compartilhamento de conta; máquina bloqueada é crítica por definição porque o grupo já a considera uma origem de risco.

## Decisões de segurança

- **Acessos imutáveis:** o arquivo só recebe linhas novas no final. Ninguém "limpa o rastro" depois de um ataque.
- **Matrícula mascarada:** na tela e no log aparece só o início da matrícula. A matrícula completa só é mostrada na opção específica, que pede motivo e deixa registro.
- **Log com operador:** o sistema registra quem usou o monitor e o que fez. Quem pode ver dados e bloquear contas também precisa ser monitorado.
- **Bloqueio automático:** após 3 falhas seguidas, o usuário é bloqueado e a ação vai para o log.
- **Selo de integridade:** cada linha de `acessos.csv` e `auditoria.csv` carrega um selo calculado a partir da linha e do selo anterior. Se alguém editar ou apagar uma linha do meio do arquivo, o sistema avisa (menu Auditoria e painel inicial).

## Diferencial: Radar Sentinela

- **Modo Investigação:** responde as três perguntas da responsável pelo laboratório (quem acessou, de onde veio, se já aconteceu antes) com a linha do tempo da conta.
- **Ranking de risco:** nota de 0 a 100 por usuário, a partir dos acessos críticos, suspeitos e das falhas.
- **Simulador:** cria usuários fictícios, gera acessos aleatórios e reproduz o "Incidente das 3h" para testar as regras.
- **Exportação:** salva o relatório de segurança em um arquivo `.txt`.
- **Selo de integridade e bloqueio automático**, descritos acima.

## O que o sistema não consegue detectar

- Apagar as últimas linhas ou o arquivo inteiro de acessos ou auditoria (o selo só detecta alteração no meio da cadeia).
- Quem conhece o cálculo do selo e refaz toda a cadeia depois de editar um arquivo. O selo é uma checagem simples, não é criptografia forte.
- Acesso feito em horário permitido, de máquina comum, com a senha correta (por exemplo, um colega usando a conta de outro).
- Qualquer coisa que não passe pelo registro de acessos, como ações dentro do computador depois do login.
- Uso de máquina compartilhada só gera alerta, e o sistema não consegue dizer quem estava na frente da máquina.

## Estrutura do projeto

```
sentinelalog.py          # programa completo, dividido em 6 partes
dados/                   # criada automaticamente
  usuarios.csv
  acessos.csv
  auditoria.csv
  maquinas_bloqueadas.txt
  relatorio_*.txt        # relatórios exportados
```

O código está dividido em 6 partes, cada uma explicada por comentários:

1. Base: constantes, arquivos, selo de integridade, auditoria e entradas
2. Usuários: cadastro, mascaramento e revelação de matrícula
3. Acessos: registro, análise de risco e detecção de risco
4. Relatório de segurança e verificação de integridade
5. Funcionalidade extra (Radar Sentinela)
6. Menu principal

## Tecnologias

Python 3, apenas com as bibliotecas `os`, `datetime` e `random`. O código usa condicionais, laços, funções, listas e manipulação de arquivos.

## Grupo

- João Filipe Revoredo silva Arruda
- Eduardo Pedrosa Miranda
- Matheus Didini Pereira Nogueira
- Luciana Gabriel Sales
- João Guilherme
- Rhandom Shieu
