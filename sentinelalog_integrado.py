import os
import hashlib
import hmac
import secrets
import getpass
import random
from datetime import datetime, timedelta

try:
    import IA
except ImportError:
    IA = None

PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")
ARQ_USUARIOS = os.path.join(PASTA_DADOS, "usuarios.csv")
ARQ_ACESSOS = os.path.join(PASTA_DADOS, "acessos.csv")
ARQ_AUDITORIA = os.path.join(PASTA_DADOS, "auditoria.csv")
ARQ_BLOQUEADAS = os.path.join(PASTA_DADOS, "maquinas_bloqueadas.txt")
SEPARADOR = ";"
FORMATO_BANCO = "%Y-%m-%d %H:%M"
FORMATO_TELA = "%d/%m/%Y %H:%M"
PERFIS = ["estudante", "professor", "administrador"]
SELO_INICIAL = "0"
OPERADOR = ["desconhecido"]
U_MATRICULA, U_NOME, U_PERFIL, U_INICIO, U_FIM, U_OBS, U_BLOQUEADO = 0, 1, 2, 3, 4, 5, 6
A_ID, A_MATRICULA, A_DATA, A_MAQUINA, A_RESULTADO, A_CLASSE, A_PONTOS, A_MOTIVOS = 0, 1, 2, 3, 4, 5, 6, 7

ARQ_OPERADORES = os.path.join(PASTA_DADOS, "operadores.csv")


NIVEIS = ["observador", "operador", "administrador", "superadmin"]
DESCRICAO_NIVEIS = [
    "só consulta (acessos, listas e usuários com matrícula mascarada)",
    "consulta + registra acessos + bloqueia usuários e máquinas",
    "administra usuários, vê a auditoria e gerencia operadores de nível menor",
    "acesso total; gerencia qualquer operador e vê tentativas de invasão",
]
NIVEL_MAXIMO = len(NIVEIS)
O_LOGIN, O_NOME, O_NIVEL, O_SAL, O_HASH, O_ATIVO, O_FALHAS, O_TROCAR, O_BLOQUEIO = 0, 1, 2, 3, 4, 5, 6, 7, 8
S_LOGIN, S_NOME, S_NIVEL = 0, 1, 2
SESSAO = ["", "", 0]
ITERACOES_HASH = 200000
LIMITE_FALHAS_LOGIN = 3
TENTATIVAS_POR_SESSAO = 3
TAMANHO_MIN_SENHA = 8
FORMATO_SEGUNDOS = "%Y-%m-%d %H:%M:%S"

SUPERADMIN_LOGIN = "joao arruda"
SUPERADMIN_NOME = "João Arruda"
SUPERADMIN_SAL = "97bbfdd7e066d8df7786938a887ae547"
SUPERADMIN_HASH = "41b3a3eef6c49ad51331d67b14255dfa8dcaa79d401512df4b593d2c09fb5e03"
TEMPO_BLOQUEIO_SUPER_MIN = 10
P_CODIGO, P_DESCRICAO, P_NIVEL = 0, 1, 2
PERMISSOES = [
    ["usuarios_listar", "Listar usuários (matrícula mascarada)", 1],
    ["usuarios_bloquear", "Bloquear / desbloquear usuário monitorado", 2],
    ["usuarios_adicionar", "Adicionar usuário monitorado", 3],
    ["usuarios_editar", "Editar usuário monitorado", 3],
    ["usuarios_excluir", "Excluir usuário monitorado", 3],
    ["usuarios_revelar", "Revelar matrícula completa (fica no log)", 3],
    ["acessos_consultar", "Consultar acessos", 1],
    ["acessos_explicar", "Explicar a classificação de um acesso", 1],
    ["acessos_registrar", "Registrar acesso", 2],
    ["deteccao_ver", "Ver máquinas compartilhadas, bloqueadas e usuários bloqueados", 1],
    ["deteccao_bloquear_maquina", "Bloquear uma máquina/origem", 2],
    ["auditoria_consultar", "Consultar o log de auditoria", 3],
    ["relatorio", "Relatório de segurança", 3],
    ["extra_consultar", "Radar Sentinela: ranking, investigação e integridade dos registros", 1],
    ["extra_simular", "Radar Sentinela: simulador com dados fictícios", 3],
    ["extra_exportar", "Radar Sentinela: exportar relatório para arquivo", 3],
    ["ia", "Assistente de IA", 2],
    ["operadores_gerenciar", "Gerenciar operadores (só os de nível abaixo do seu)", 3],
    ["operadores_tentativas", "Ver tentativas de login suspeitas e acessos negados", 4],
    ["conta_propria", "Alterar a própria senha e ver as próprias permissões", 1],
]


def limpar_campo(texto):
    return str(texto).replace(SEPARADOR, ",").replace("\n", " ").replace("\r", " ").strip()


def preparar_arquivos():
    try:
        os.makedirs(PASTA_DADOS, exist_ok=True)
        for caminho in [ARQ_USUARIOS, ARQ_ACESSOS, ARQ_AUDITORIA, ARQ_OPERADORES]:
            if not os.path.exists(caminho):
                arquivo = open(caminho, "w", encoding="utf-8")
                arquivo.close()
        if not os.path.exists(ARQ_BLOQUEADAS):
            arquivo = open(ARQ_BLOQUEADAS, "w", encoding="utf-8")
            arquivo.write("# Maquinas/origens bloqueadas (uma por linha)\nPC-99\nREMOTO-01\n")
            arquivo.close()
        return True
    except OSError:
        print("[ERRO] Não foi possível criar os arquivos de dados.")
        return False


def ler_linhas(caminho):
    linhas = []
    try:
        arquivo = open(caminho, "r", encoding="utf-8")
        for linha in arquivo:
            linha = linha.strip()
            if linha != "":
                linhas.append(linha.split(SEPARADOR))
        arquivo.close()
    except OSError:
        print(f"[ERRO] Não foi possível ler o arquivo {os.path.basename(caminho)}.")
    return linhas


def gravar_linhas(caminho, linhas, modo="w"):
    try:
        arquivo = open(caminho, modo, encoding="utf-8")
        for campos in linhas:
            texto = []
            for campo in campos:
                texto.append(limpar_campo(campo))
            arquivo.write(SEPARADOR.join(texto) + "\n")
        arquivo.close()
        return True
    except OSError:
        print(f"[ERRO] Não foi possível gravar em {os.path.basename(caminho)}.")
        return False


def calcular_selo(texto):
    valor = 7
    for letra in texto:
        valor = (valor * 131 + ord(letra)) % 2305843009213693951
    return str(valor)


def anexar_linha_selada(caminho, campos):
    linhas = ler_linhas(caminho)
    selo_anterior = SELO_INICIAL
    if len(linhas) > 0:
        selo_anterior = linhas[-1][-1]
    texto = []
    for campo in campos:
        texto.append(limpar_campo(campo))
    selo = calcular_selo(selo_anterior + "|" + SEPARADOR.join(texto))
    return gravar_linhas(caminho, [texto + [selo]], "a")


def registrar_auditoria(operacao, afetado="-", detalhe="-"):
    momento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    anexar_linha_selada(ARQ_AUDITORIA, [momento, OPERADOR[0], operacao, afetado, detalhe])


def consultar_auditoria():
    if not exigir("auditoria_consultar"):
        return
    linhas = ler_linhas(ARQ_AUDITORIA)
    if len(linhas) == 0:
        print("  O log de auditoria está vazio.")
        return
    quantidade = ler_inteiro(f"  Quantas linhas mostrar? (1-{len(linhas)}, Enter = 20): ",
                             1, len(linhas), min(20, len(linhas)))
    print(f"\n  {'Data/hora':<20}{'Operador':<14}{'Operação':<26}{'Usuário afetado':<28}Detalhe")
    print("  " + "-" * 100)
    for linha in linhas[-quantidade:]:
        if len(linha) == 6:
            print(f"  {linha[0]:<20}{linha[1][:12]:<14}{linha[2]:<26}{linha[3][:26]:<28}{linha[4]}")


def pausar():
    input("\nPressione Enter para continuar...")


def mostrar_titulo(texto):
    print("=" * 62)
    print(texto.center(62))
    print("=" * 62)


def confirmar(mensagem):
    return input(mensagem + " (s/n): ").strip().lower() == "s"


def ler_texto(mensagem, obrigatorio=True, maximo=60):
    while True:
        valor = limpar_campo(input(mensagem))
        if valor == "" and obrigatorio:
            print("  Este campo não pode ficar vazio.")
        elif len(valor) > maximo:
            print(f"  Use no máximo {maximo} caracteres.")
        else:
            return valor


def ler_inteiro(mensagem, minimo, maximo, atual=-1):
    while True:
        texto = input(mensagem).strip()
        if texto == "" and atual != -1:
            return atual
        try:
            numero = int(texto)
            if minimo <= numero <= maximo:
                return numero
            print(f"  Digite um valor entre {minimo} e {maximo}.")
        except ValueError:
            print("  Digite um número inteiro.")


def ler_data_hora(mensagem):
    while True:
        texto = input(mensagem).strip()
        if texto == "":
            return datetime.now().strftime(FORMATO_BANCO)
        try:
            return datetime.strptime(texto, FORMATO_TELA).strftime(FORMATO_BANCO)
        except ValueError:
            print("  Formato inválido. Use DD/MM/AAAA HH:MM (ex.: 25/10/2026 03:15).")


def formatar_data(data_hora):
    try:
        return datetime.strptime(data_hora, FORMATO_BANCO).strftime(FORMATO_TELA)
    except ValueError:
        return data_hora


def escolher_opcao(titulo, opcoes, texto_zero="Voltar"):
    print()
    mostrar_titulo(titulo)
    for i in range(len(opcoes)):
        print(f"  {i + 1}. {opcoes[i]}")
    print(f"  0. {texto_zero}")
    return ler_inteiro("\nEscolha uma opção: ", 0, len(opcoes))


# =====================================================================
# CONTROLE DE ACESSO: permissões, senhas, login e gestão de operadores
# =====================================================================
def nome_nivel(nivel):
    if nivel < 1 or nivel > NIVEL_MAXIMO:
        return "sem sessão"
    return NIVEIS[nivel - 1]


def nivel_minimo(codigo):
    for p in PERMISSOES:
        if p[P_CODIGO] == codigo:
            return p[P_NIVEL]
    return NIVEL_MAXIMO          # código desconhecido: só o nível mais alto (falha segura)


def tem_permissao(codigo):
    return SESSAO[S_NIVEL] >= nivel_minimo(codigo)


def exigir(codigo):
    """Confere a permissão ANTES de executar uma ação. Se negar, registra no log."""
    if tem_permissao(codigo):
        return True
    minimo = nivel_minimo(codigo)
    print(f"  [ACESSO NEGADO] Esta ação exige o nível '{nome_nivel(minimo)}' ou superior. "
          f"Seu nível: '{nome_nivel(SESSAO[S_NIVEL])}'.")
    registrar_auditoria("ACESSO_NEGADO", "-", f"acao={codigo}, exige={nome_nivel(minimo)}")
    return False


def escolher_opcao_nivel(titulo, itens, texto_zero="Voltar"):
    """Como escolher_opcao, mas só mostra os itens que o nível da sessão permite.
    Cada item é [texto, código_da_permissão]. Devolve a posição ORIGINAL do item
    (1, 2, 3...) para o seu if/elif continuar igual, ou 0 para voltar."""
    posicoes = []
    textos = []
    for i in range(len(itens)):
        if tem_permissao(itens[i][1]):
            posicoes.append(i + 1)
            textos.append(itens[i][0])
    opcao = escolher_opcao(titulo, textos, texto_zero)
    if opcao == 0:
        return 0
    return posicoes[opcao - 1]


def pode_gerenciar(nivel_alvo):
    """Regra da hierarquia: superadmin gerencia todos; os demais só gerenciam
    contas de nível MENOR que o seu (e só se tiverem a permissão de gerenciar)."""
    if SESSAO[S_NIVEL] >= NIVEL_MAXIMO:
        return True
    return tem_permissao("operadores_gerenciar") and nivel_alvo < SESSAO[S_NIVEL]


def nivel_maximo_atribuivel():
    if SESSAO[S_NIVEL] >= NIVEL_MAXIMO:
        return NIVEL_MAXIMO
    return SESSAO[S_NIVEL] - 1


# ---------- senhas ----------
def gerar_hash(senha, sal):
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(sal), ITERACOES_HASH).hex()


def senha_confere(senha, sal, hash_guardado):
    return hmac.compare_digest(gerar_hash(senha, sal), hash_guardado)


def senha_valida(senha):
    tem_letra = False
    tem_numero = False
    for caractere in senha:
        if caractere.isalpha():
            tem_letra = True
        if caractere.isdigit():
            tem_numero = True
    return len(senha) >= TAMANHO_MIN_SENHA and tem_letra and tem_numero


def gerar_senha_temporaria():
    return secrets.token_hex(5)          # 10 caracteres aleatórios


def ler_senha(mensagem):
    return getpass.getpass(mensagem)     # não mostra o que é digitado


def ler_nova_senha():
    while True:
        senha = ler_senha("  Nova senha: ")
        if not senha_valida(senha):
            print(f"  A senha precisa ter pelo menos {TAMANHO_MIN_SENHA} caracteres, com letras e números.")
            continue
        if ler_senha("  Repita a nova senha: ") != senha:
            print("  As senhas não conferem. Tente de novo.")
            continue
        return senha


def definir_senha(operador, senha, trocar):
    operador[O_SAL] = secrets.token_hex(16)
    operador[O_HASH] = gerar_hash(senha, operador[O_SAL])
    operador[O_TROCAR] = trocar
    operador[O_FALHAS] = "0"
    operador[O_BLOQUEIO] = "0"


def montar_operador(login, nome, nivel, senha, trocar):
    operador = [login, nome, str(nivel), "", "", "1", "0", trocar, "0"]
    definir_senha(operador, senha, trocar)
    return operador


def carregar_operadores():
    operadores = []
    for linha in ler_linhas(ARQ_OPERADORES):
        if len(linha) == 8:                
            linha.append("0")
        if len(linha) == 9 and linha[O_NIVEL].isdigit() and linha[O_FALHAS].isdigit():
            if 1 <= int(linha[O_NIVEL]) <= NIVEL_MAXIMO:
                operadores.append(linha)
    return operadores


def salvar_operadores(operadores):
    return gravar_linhas(ARQ_OPERADORES, operadores)


def buscar_operador(login, operadores):
    for i in range(len(operadores)):
        if operadores[i][O_LOGIN] == login:
            return i
    return -1


def contar_superadmins_ativos(operadores, ignorar=-1):
    total = 0
    for i in range(len(operadores)):
        if i != ignorar and int(operadores[i][O_NIVEL]) == NIVEL_MAXIMO and operadores[i][O_ATIVO] == "1":
            total += 1
    return total


def ler_login_novo(operadores):
    while True:
        login = ler_texto("  Login (3 a 20 letras/números, sem espaços): ", True, 20).lower()
        if len(login) < 3 or not login.isalnum() or not login.isascii():
            print("  Use de 3 a 20 caracteres, só letras (sem acento) e números.")
        elif buscar_operador(login, operadores) != -1:
            print("  Já existe um operador com esse login.")
        else:
            return login


# ---------- primeira execução e login ----------
def eh_superadmin_fixo(login):
    return login == SUPERADMIN_LOGIN


def garantir_superadmin_fixo():
    """Cria ou restaura a conta do superadmin fixo. Roda toda vez que o programa abre:
    se alguém tiver editado o operadores.csv, o que foi mexido volta ao valor do código
    e o fato fica registrado na auditoria."""
    operadores = carregar_operadores()
    posicao = buscar_operador(SUPERADMIN_LOGIN, operadores)
    esperado = [SUPERADMIN_LOGIN, SUPERADMIN_NOME, str(NIVEL_MAXIMO), SUPERADMIN_SAL, SUPERADMIN_HASH, "1"]
    nomes_campos = ["login", "nome", "nível", "sal", "senha", "status"]
    if posicao == -1:
        operadores.append(esperado + ["0", "0", "0"])
        operacao = "SUPERADMIN_CRIADO"
        detalhe = "conta fixa do sistema"
    else:
        atual = operadores[posicao]
        diferentes = []
        for i in range(len(esperado)):
            if atual[i] != esperado[i]:
                diferentes.append(nomes_campos[i])
                atual[i] = esperado[i]
        if atual[O_TROCAR] != "0":
            diferentes.append("troca de senha")
            atual[O_TROCAR] = "0"
        if len(diferentes) == 0:
            return True
        operacao = "SUPERADMIN_RESTAURADO"
        detalhe = "alterado fora do sistema: " + ", ".join(diferentes)
    if not salvar_operadores(operadores):
        return False
    registrar_auditoria(operacao, SUPERADMIN_LOGIN, detalhe)
    return True


def trocar_senha_obrigatoria(operadores, posicao):
    operador = operadores[posicao]
    while True:
        nova = ler_nova_senha()
        if senha_confere(nova, operador[O_SAL], operador[O_HASH]):
            print("  A nova senha precisa ser diferente da temporária.")
            continue
        definir_senha(operador, nova, "0")
        if salvar_operadores(operadores):
            registrar_auditoria("SENHA_ALTERADA", operador[O_LOGIN], "troca obrigatória (senha temporária)")
            print("  Senha atualizada.")
            return


def liberar_se_bloqueio_expirou(operador):
    """O bloqueio do superadmin fixo é temporário; os demais só são liberados por um nível acima."""
    if eh_superadmin_fixo(operador[O_LOGIN]) and int(operador[O_FALHAS]) >= LIMITE_FALHAS_LOGIN:
        if operador[O_BLOQUEIO] <= datetime.now().strftime(FORMATO_SEGUNDOS):
            operador[O_FALHAS] = "0"
            operador[O_BLOQUEIO] = "0"


def tentar_login(login, senha):
    """Devolve: 'ok', 'erro' (1º erro), 'aviso' (2º erro), 'bloqueou' (3º erro) ou 'bloqueada' (já estava)."""
    operadores = carregar_operadores()
    posicao = buscar_operador(login, operadores)
    if posicao == -1:
        registrar_auditoria("LOGIN_FALHA", limpar_campo(login), "login inexistente")
        return "erro"
    operador = operadores[posicao]
    liberar_se_bloqueio_expirou(operador)
    if operador[O_ATIVO] != "1":
        registrar_auditoria("LOGIN_FALHA", login, "conta desativada")
        return "erro"
    if int(operador[O_FALHAS]) >= LIMITE_FALHAS_LOGIN:
        registrar_auditoria("LOGIN_FALHA", login, "tentativa em conta bloqueada")
        return "bloqueada"

    if not senha_confere(senha, operador[O_SAL], operador[O_HASH]):
        falhas = int(operador[O_FALHAS]) + 1
        operador[O_FALHAS] = str(falhas)
        detalhe = f"senha incorreta ({falhas}/{LIMITE_FALHAS_LOGIN})"
        if falhas >= LIMITE_FALHAS_LOGIN:
            if eh_superadmin_fixo(login):
                libera_em = datetime.now() + timedelta(minutes=TEMPO_BLOQUEIO_SUPER_MIN)
                operador[O_BLOQUEIO] = libera_em.strftime(FORMATO_SEGUNDOS)
            salvar_operadores(operadores)
            registrar_auditoria("CONTA_BLOQUEADA_LOGIN", login, detalhe)
            return "bloqueou"
        salvar_operadores(operadores)
        registrar_auditoria("LOGIN_FALHA", login, detalhe)
        if falhas == LIMITE_FALHAS_LOGIN - 1:
            return "aviso"
        return "erro"

    operador[O_FALHAS] = "0"
    operador[O_BLOQUEIO] = "0"
    salvar_operadores(operadores)
    SESSAO[S_LOGIN] = login
    SESSAO[S_NOME] = operador[O_NOME]
    SESSAO[S_NIVEL] = int(operador[O_NIVEL])
    OPERADOR[0] = login
    registrar_auditoria("LOGIN_OK", login, f"nivel={nome_nivel(SESSAO[S_NIVEL])}")
    if operador[O_TROCAR] == "1":
        print("\n  Sua senha é temporária. Defina uma nova senha para continuar.")
        trocar_senha_obrigatoria(operadores, posicao)
    return "ok"


def autenticar():
    print("--- Login ---")
    for tentativa in range(TENTATIVAS_POR_SESSAO):
        login = ler_texto("  Login: ", True, 20).lower()
        senha = ler_senha("  Senha: ")
        resultado = tentar_login(login, senha)
        if resultado == "ok":
            print(f"\n  Bem-vindo(a), {SESSAO[S_NOME]}! Nível: {nome_nivel(SESSAO[S_NIVEL])}.")
            return True
        if resultado == "aviso":
            print("  [ATENÇÃO] Você errou a senha 2 vezes. Mais um erro e a conta será BLOQUEADA.")
        elif resultado == "bloqueou":
            print("  [CONTA BLOQUEADA] Senha incorreta 3 vezes seguidas.")
            if eh_superadmin_fixo(login):
                print(f"  Por segurança, ela só poderá ser usada de novo em {TEMPO_BLOQUEIO_SUPER_MIN} minutos.")
            else:
                print("  Procure um operador de nível superior ao seu para desbloquear.")
            return False
        elif resultado == "bloqueada":
            print("  [CONTA BLOQUEADA] Esta conta está bloqueada por excesso de tentativas.")
            if eh_superadmin_fixo(login):
                print(f"  Aguarde o fim do bloqueio temporário ({TEMPO_BLOQUEIO_SUPER_MIN} minutos após o 3º erro).")
            else:
                print("  Procure um operador de nível superior ao seu para desbloquear.")
            return False
        else:
            print("  Login ou senha incorretos.")
    print("  Número máximo de tentativas atingido. Encerrando.")
    return False


def alterar_minha_senha():
    if not exigir("conta_propria"):
        return
    if eh_superadmin_fixo(SESSAO[S_LOGIN]):
        print("  A senha do superadmin é fixa (definida no código) e não pode ser alterada por aqui.")
        return
    operadores = carregar_operadores()
    posicao = buscar_operador(SESSAO[S_LOGIN], operadores)
    if posicao == -1:
        print("  Sua conta não foi encontrada.")
        return
    operador = operadores[posicao]
    atual = ler_senha("  Senha atual: ")
    if not senha_confere(atual, operador[O_SAL], operador[O_HASH]):
        print("  Senha atual incorreta.")
        registrar_auditoria("SENHA_ALTERACAO_FALHA", SESSAO[S_LOGIN], "senha atual incorreta")
        return
    nova = ler_nova_senha()
    if senha_confere(nova, operador[O_SAL], operador[O_HASH]):
        print("  A nova senha precisa ser diferente da atual.")
        return
    definir_senha(operador, nova, "0")
    if salvar_operadores(operadores):
        registrar_auditoria("SENHA_ALTERADA", SESSAO[S_LOGIN], "troca feita pelo próprio operador")
        print("  Senha alterada com sucesso.")


def mostrar_permissoes():
    print(f"\n  Operador: {SESSAO[S_LOGIN]} | Nível: {nome_nivel(SESSAO[S_NIVEL])}")
    print("\n  Os níveis:")
    for i in range(NIVEL_MAXIMO):
        print(f"    {i + 1}. {NIVEIS[i]:<14} {DESCRICAO_NIVEIS[i]}")
    print(f"\n  {'Ação':<64}{'Exige':<15}Você pode?")
    print("  " + "-" * 92)
    for p in PERMISSOES:
        pode = "não"
        if tem_permissao(p[P_CODIGO]):
            pode = "SIM"
        print(f"  {p[P_DESCRICAO][:62]:<64}{nome_nivel(p[P_NIVEL]):<15}{pode}")


def menu_minha_conta():
    while True:
        opcao = escolher_opcao_nivel("MINHA CONTA", [
            ["Alterar minha senha", "conta_propria"],
            ["Ver meu nível e minhas permissões", "conta_propria"],
        ])
        if opcao == 0:
            return
        elif opcao == 1:
            alterar_minha_senha()
        elif opcao == 2:
            mostrar_permissoes()
        pausar()


def listar_operadores(operadores):
    print(f"\n{'Nº':>3}  {'Login':<14}{'Nome':<24}{'Nível':<15}Status")
    print("-" * 80)
    for i in range(len(operadores)):
        o = operadores[i]
        liberar_se_bloqueio_expirou(o)
        status = "ativo"
        if o[O_ATIVO] != "1":
            status = "DESATIVADO"
        elif int(o[O_FALHAS]) >= LIMITE_FALHAS_LOGIN:
            status = "BLOQUEADO (tentativas)"
            if eh_superadmin_fixo(o[O_LOGIN]):
                status = f"BLOQUEADO até {o[O_BLOQUEIO][11:16]}"
        elif o[O_TROCAR] == "1":
            status = "ativo (senha temporária)"
        if eh_superadmin_fixo(o[O_LOGIN]):
            status += "  [conta fixa]"
        if o[O_LOGIN] == SESSAO[S_LOGIN]:
            status += "  <- você"
        print(f"{i + 1:>3}  {o[O_LOGIN]:<14}{o[O_NOME][:22]:<24}{nome_nivel(int(o[O_NIVEL])):<15}{status}")


def selecionar_operador(operadores, acao):
    listar_operadores(operadores)
    numero = ler_inteiro(f"\nNúmero do operador para {acao} (0 = cancelar): ", 0, len(operadores))
    return numero - 1


def selecionar_operador_gerenciavel(operadores, acao, permitir_fixo=False):
    """Escolhe um operador e aplica as regras da hierarquia. Devolve a posição ou -1."""
    posicao = selecionar_operador(operadores, acao)
    if posicao == -1:
        return -1
    alvo = operadores[posicao]
    if alvo[O_LOGIN] == SESSAO[S_LOGIN]:
        print("  Você não pode fazer isso na sua própria conta (para a senha, use 'Minha conta').")
        return -1
    if eh_superadmin_fixo(alvo[O_LOGIN]) and not permitir_fixo:
        print("  A conta do superadmin fixo é definida no código e não pode ser alterada pelo sistema.")
        registrar_auditoria("ACESSO_NEGADO", alvo[O_LOGIN], f"conta fixa: acao={acao}")
        return -1
    if not pode_gerenciar(int(alvo[O_NIVEL])):
        print(f"  [HIERARQUIA] Você ('{nome_nivel(SESSAO[S_NIVEL])}') só gerencia operadores de nível inferior ao seu.")
        registrar_auditoria("ACESSO_NEGADO", alvo[O_LOGIN], f"hierarquia: acao={acao}")
        return -1
    return posicao


def escolher_nivel(maximo):
    for i in range(maximo):
        print(f"    {i + 1}. {NIVEIS[i]:<14} {DESCRICAO_NIVEIS[i]}")
    return ler_inteiro("  Nível (0 = cancelar): ", 0, maximo)


def criar_operador():
    if not exigir("operadores_gerenciar"):
        return
    operadores = carregar_operadores()
    print("\n--- Novo operador ---")
    login = ler_login_novo(operadores)
    nome = ler_texto("  Nome: ", True, 40)
    maximo = nivel_maximo_atribuivel()
    print(f"  Níveis que você pode conceder (até '{nome_nivel(maximo)}'):")
    nivel = escolher_nivel(maximo)
    if nivel == 0:
        print("  Operação cancelada.")
        return
    senha = gerar_senha_temporaria()
    operadores.append(montar_operador(login, nome, nivel, senha, "1"))
    if salvar_operadores(operadores):
        registrar_auditoria("OPERADOR_CRIADO", login, f"nivel={nome_nivel(nivel)}")
        print(f"\n  Operador '{login}' criado com o nível '{nome_nivel(nivel)}'.")
        print(f"  Senha temporária: {senha}")
        print("  Anote e entregue em mãos: ela não será mostrada de novo e a troca é obrigatória no 1º login.")


def alterar_nivel_operador():
    if not exigir("operadores_gerenciar"):
        return
    operadores = carregar_operadores()
    posicao = selecionar_operador_gerenciavel(operadores, "alterar o nível")
    if posicao == -1:
        return
    alvo = operadores[posicao]
    nivel_atual = int(alvo[O_NIVEL])
    print(f"  Nível atual de {alvo[O_LOGIN]}: {nome_nivel(nivel_atual)}")
    print(f"  Novo nível (você pode conceder até '{nome_nivel(nivel_maximo_atribuivel())}'):")
    novo = escolher_nivel(nivel_maximo_atribuivel())
    if novo == 0 or novo == nivel_atual:
        print("  Nada foi alterado.")
        return
    if nivel_atual == NIVEL_MAXIMO and alvo[O_ATIVO] == "1" and contar_superadmins_ativos(operadores, posicao) == 0:
        print("  Operação negada: o sistema precisa ter pelo menos um superadmin ativo.")
        registrar_auditoria("ACESSO_NEGADO", alvo[O_LOGIN], "tentou rebaixar o último superadmin")
        return
    alvo[O_NIVEL] = str(novo)
    if salvar_operadores(operadores):
        registrar_auditoria("OPERADOR_NIVEL_ALTERADO", alvo[O_LOGIN],
                            f"de={nome_nivel(nivel_atual)}, para={nome_nivel(novo)}")
        print(f"  {alvo[O_LOGIN]} agora é '{nome_nivel(novo)}'. Vale a partir do próximo login dele(a).")


def redefinir_senha_operador():
    if not exigir("operadores_gerenciar"):
        return
    operadores = carregar_operadores()
    posicao = selecionar_operador_gerenciavel(operadores, "redefinir a senha")
    if posicao == -1:
        return
    alvo = operadores[posicao]
    if not confirmar(f"  Gerar uma nova senha temporária para {alvo[O_LOGIN]}?"):
        print("  Operação cancelada.")
        return
    senha = gerar_senha_temporaria()
    definir_senha(alvo, senha, "1")
    if salvar_operadores(operadores):
        registrar_auditoria("SENHA_REDEFINIDA", alvo[O_LOGIN], "senha temporária gerada")
        print(f"  Nova senha temporária de {alvo[O_LOGIN]}: {senha}")
        print("  A troca é obrigatória no próximo login. A conta também foi desbloqueada.")


def desbloquear_operador():
    if not exigir("operadores_gerenciar"):
        return
    operadores = carregar_operadores()
    posicao = selecionar_operador_gerenciavel(operadores, "desbloquear", True)
    if posicao == -1:
        return
    alvo = operadores[posicao]
    liberar_se_bloqueio_expirou(alvo)
    if int(alvo[O_FALHAS]) < LIMITE_FALHAS_LOGIN:
        print("  Esta conta não está bloqueada por tentativas de login.")
        return
    alvo[O_FALHAS] = "0"
    alvo[O_BLOQUEIO] = "0"
    if salvar_operadores(operadores):
        registrar_auditoria("OPERADOR_DESBLOQUEADO", alvo[O_LOGIN], "tentativas de login zeradas")
        print("  Conta desbloqueada.")


def alternar_ativo_operador():
    if not exigir("operadores_gerenciar"):
        return
    operadores = carregar_operadores()
    posicao = selecionar_operador_gerenciavel(operadores, "desativar/reativar")
    if posicao == -1:
        return
    alvo = operadores[posicao]
    if alvo[O_ATIVO] == "1":
        if int(alvo[O_NIVEL]) == NIVEL_MAXIMO and contar_superadmins_ativos(operadores, posicao) == 0:
            print("  Operação negada: o sistema precisa ter pelo menos um superadmin ativo.")
            registrar_auditoria("ACESSO_NEGADO", alvo[O_LOGIN], "tentou desativar o último superadmin")
            return
        if not confirmar(f"  Desativar {alvo[O_LOGIN]}? Ele(a) não conseguirá mais entrar"):
            print("  Operação cancelada.")
            return
        alvo[O_ATIVO] = "0"
        operacao = "OPERADOR_DESATIVADO"
    else:
        alvo[O_ATIVO] = "1"
        alvo[O_FALHAS] = "0"
        operacao = "OPERADOR_REATIVADO"
    if salvar_operadores(operadores):
        registrar_auditoria(operacao, alvo[O_LOGIN])
        print("  Status atualizado.")


def ver_tentativas_suspeitas():
    if not exigir("operadores_tentativas"):
        return
    eventos = ["LOGIN_FALHA", "CONTA_BLOQUEADA_LOGIN", "ACESSO_NEGADO", "SENHA_ALTERACAO_FALHA"]
    filtradas = []
    for linha in ler_linhas(ARQ_AUDITORIA):
        if len(linha) == 6 and linha[2] in eventos:
            filtradas.append(linha)
    if len(filtradas) == 0:
        print("  Nenhuma tentativa suspeita registrada.")
        return
    print(f"\n  {'Data/hora':<20}{'Operador':<14}{'Evento':<26}{'Alvo':<16}Detalhe")
    print("  " + "-" * 100)
    for linha in filtradas[-20:]:
        print(f"  {linha[0]:<20}{linha[1][:12]:<14}{linha[2]:<26}{linha[3][:14]:<16}{linha[4]}")
    print(f"\n  {len(filtradas)} evento(s) no total (mostrando até 20).")


def menu_operadores():
    while True:
        opcao = escolher_opcao_nivel("OPERADORES (CONTAS E NÍVEIS)", [
            ["Listar operadores", "operadores_gerenciar"],
            ["Criar operador", "operadores_gerenciar"],
            ["Alterar nível de um operador", "operadores_gerenciar"],
            ["Redefinir senha de um operador", "operadores_gerenciar"],
            ["Desbloquear conta (tentativas de login)", "operadores_gerenciar"],
            ["Desativar / reativar operador", "operadores_gerenciar"],
            ["Tentativas de login suspeitas e acessos negados", "operadores_tentativas"],
        ])
        if opcao == 0:
            return
        elif opcao == 1:
            if exigir("operadores_gerenciar"):
                listar_operadores(carregar_operadores())
        elif opcao == 2:
            criar_operador()
        elif opcao == 3:
            alterar_nivel_operador()
        elif opcao == 4:
            redefinir_senha_operador()
        elif opcao == 5:
            desbloquear_operador()
        elif opcao == 6:
            alternar_ativo_operador()
        elif opcao == 7:
            ver_tentativas_suspeitas()
        pausar()


def carregar_usuarios():
    usuarios = []
    for linha in ler_linhas(ARQ_USUARIOS):
        if len(linha) == 7 and linha[U_INICIO].isdigit() and linha[U_FIM].isdigit():
            usuarios.append(linha)
    return usuarios


def salvar_usuarios(usuarios):
    return gravar_linhas(ARQ_USUARIOS, usuarios)


def mascarar_matricula(matricula):
    if len(matricula) <= 2:
        return "*" * len(matricula)
    return matricula[:2] + "*" * (len(matricula) - 2)


def buscar_usuario(matricula, usuarios):
    for i in range(len(usuarios)):
        if usuarios[i][U_MATRICULA] == matricula:
            return i
    return -1


def rotulo_matricula(matricula, usuarios):
    posicao = buscar_usuario(matricula, usuarios)
    if posicao == -1:
        return f"desconhecido ({mascarar_matricula(matricula)})"
    return f"{usuarios[posicao][U_NOME]} ({mascarar_matricula(matricula)})"


def dentro_do_horario(hora, inicio, fim):
    if inicio < fim:
        return inicio <= hora < fim
    if inicio > fim:
        return hora >= inicio or hora < fim
    return False


def listar_usuarios(usuarios):
    print(f"\n{'Nº':>3}  {'Matrícula':<12} {'Nome':<24}{'Perfil':<15}{'Horário':<10}{'Status':<11}Obs")
    print("-" * 85)
    for i in range(len(usuarios)):
        u = usuarios[i]
        status = "ativo"
        if u[U_BLOQUEADO] == "1":
            status = "BLOQUEADO"
        horario = f"{int(u[U_INICIO]):02d}h-{int(u[U_FIM]):02d}h"
        print(f"{i + 1:>3}  {mascarar_matricula(u[U_MATRICULA]):<12} {u[U_NOME][:22]:<24}"
              f"{u[U_PERFIL]:<15}{horario:<10}{status:<11}{u[U_OBS][:25]}")


def selecionar_usuario(usuarios, acao):
    if len(usuarios) == 0:
        print("  Nenhum usuário cadastrado.")
        return -1
    listar_usuarios(usuarios)
    numero = ler_inteiro(f"\nNúmero do usuário para {acao} (0 = cancelar): ", 0, len(usuarios))
    return numero - 1


def ler_matricula_nova(usuarios):
    while True:
        matricula = ler_texto("  Matrícula (4 a 12 letras/números): ", True, 12).upper()
        if len(matricula) < 4 or not matricula.isalnum():
            print("  Use de 4 a 12 caracteres, só letras e números.")
        elif buscar_usuario(matricula, usuarios) != -1:
            print("  Já existe um usuário com essa matrícula.")
        else:
            return matricula


def escolher_perfil(atual=""):
    for i in range(len(PERFIS)):
        print(f"    {i + 1}. {PERFIS[i]}")
    padrao = -1
    if atual != "":
        padrao = 0
    escolha = ler_inteiro("  Perfil: ", 0, len(PERFIS), padrao)
    if escolha == 0:
        return atual
    return PERFIS[escolha - 1]


def ler_horario(inicio_atual=-1, fim_atual=-1):
    while True:
        inicio = ler_inteiro("  Hora inicial permitida (0-23): ", 0, 23, inicio_atual)
        fim = ler_inteiro("  Hora final permitida (1-24): ", 1, 24, fim_atual)
        if inicio != fim:
            return [inicio, fim]
        print("  Início e fim não podem ser iguais.")


def adicionar_usuario():
    if not exigir("usuarios_adicionar"):
        return
    usuarios = carregar_usuarios()
    print("\n--- Novo usuário ---")
    matricula = ler_matricula_nova(usuarios)
    nome = ler_texto("  Nome: ", True, 40)
    perfil = escolher_perfil()
    horario = ler_horario()
    obs = ler_texto("  Observações (Enter para pular): ", False, 100)
    usuarios.append([matricula, nome, perfil, str(horario[0]), str(horario[1]), obs, "0"])
    if salvar_usuarios(usuarios):
        registrar_auditoria("USUARIO_CRIADO", rotulo_matricula(matricula, usuarios), f"perfil={perfil}")
        print("  Usuário cadastrado com sucesso.")


def editar_usuario():
    if not exigir("usuarios_editar"):
        return
    usuarios = carregar_usuarios()
    posicao = selecionar_usuario(usuarios, "editar")
    if posicao == -1:
        return
    u = usuarios[posicao]
    print("  (Enter mantém o valor atual. A matrícula não pode ser alterada.)")
    nome = ler_texto(f"  Nome [{u[U_NOME]}]: ", False, 40)
    if nome != "":
        u[U_NOME] = nome
    u[U_PERFIL] = escolher_perfil(u[U_PERFIL])
    horario = ler_horario(int(u[U_INICIO]), int(u[U_FIM]))
    u[U_INICIO] = str(horario[0])
    u[U_FIM] = str(horario[1])
    obs = ler_texto(f"  Observações [{u[U_OBS]}]: ", False, 100)
    if obs != "":
        u[U_OBS] = obs
    if salvar_usuarios(usuarios):
        registrar_auditoria("USUARIO_EDITADO", rotulo_matricula(u[U_MATRICULA], usuarios))
        print("  Usuário atualizado.")


def excluir_usuario():
    if not exigir("usuarios_excluir"):
        return
    usuarios = carregar_usuarios()
    posicao = selecionar_usuario(usuarios, "excluir")
    if posicao == -1:
        return
    rotulo = rotulo_matricula(usuarios[posicao][U_MATRICULA], usuarios)
    if not confirmar(f"  Excluir {rotulo}? Os acessos antigos continuam no histórico"):
        print("  Operação cancelada.")
        return
    usuarios.pop(posicao)
    if salvar_usuarios(usuarios):
        registrar_auditoria("USUARIO_EXCLUIDO", rotulo)
        print("  Usuário excluído.")


def revelar_matricula():
    if not exigir("usuarios_revelar"):
        return
    usuarios = carregar_usuarios()
    posicao = selecionar_usuario(usuarios, "revelar a matrícula")
    if posicao == -1:
        return
    u = usuarios[posicao]
    motivo = ler_texto("  Motivo da consulta (obrigatório): ", True, 80)
    print(f"\n  Matrícula de {u[U_NOME]}: {u[U_MATRICULA]}")
    registrar_auditoria("MATRICULA_REVELADA", rotulo_matricula(u[U_MATRICULA], usuarios), f"motivo={motivo}")


def alternar_bloqueio():
    if not exigir("usuarios_bloquear"):
        return
    usuarios = carregar_usuarios()
    posicao = selecionar_usuario(usuarios, "bloquear/desbloquear")
    if posicao == -1:
        return
    u = usuarios[posicao]
    if u[U_BLOQUEADO] == "1":
        u[U_BLOQUEADO] = "0"
        operacao = "USUARIO_DESBLOQUEADO"
    else:
        u[U_BLOQUEADO] = "1"
        operacao = "USUARIO_BLOQUEADO_MANUAL"
    if salvar_usuarios(usuarios):
        registrar_auditoria(operacao, rotulo_matricula(u[U_MATRICULA], usuarios))
        print("  Status atualizado.")


def menu_usuarios():
    while True:
        opcao = escolher_opcao_nivel("USUÁRIOS", [
            ["Adicionar usuário", "usuarios_adicionar"],
            ["Listar usuários (matrícula mascarada)", "usuarios_listar"],
            ["Editar usuário", "usuarios_editar"],
            ["Excluir usuário", "usuarios_excluir"],
            ["Revelar matrícula (fica no log)", "usuarios_revelar"],
            ["Bloquear / desbloquear usuário", "usuarios_bloquear"],
        ])
        if opcao == 0:
            return
        elif opcao == 1:
            adicionar_usuario()
        elif opcao == 2:
            if exigir("usuarios_listar"):
                usuarios = carregar_usuarios()
                if len(usuarios) == 0:
                    print("  Nenhum usuário cadastrado.")
                else:
                    listar_usuarios(usuarios)
        elif opcao == 3:
            editar_usuario()
        elif opcao == 4:
            excluir_usuario()
        elif opcao == 5:
            revelar_matricula()
        elif opcao == 6:
            alternar_bloqueio()
        pausar()


PESO_FALHA = 10
PESO_FORA_HORARIO = 30
PESO_MADRUGADA = 20
PESO_PERFIL = 20
PESO_MAQUINA_BLOQUEADA = 70
PESO_MATRICULA_DESCONHECIDA = 35
PESO_USUARIO_BLOQUEADO = 40
PESO_FALHAS_SEGUIDAS = 25
PESO_TROCA_RAPIDA = 30
LIMITE_SUSPEITO = 30
LIMITE_CRITICO = 70
LIMITE_FALHAS = 3
JANELA_TROCA_MIN = 5


def carregar_acessos():
    acessos = []
    for linha in ler_linhas(ARQ_ACESSOS):
        if len(linha) == 9 and linha[A_ID].isdigit() and linha[A_PONTOS].isdigit() and len(linha[A_DATA]) == 16:
            acessos.append(linha)
    return acessos


def carregar_maquinas_bloqueadas():
    bloqueadas = []
    try:
        arquivo = open(ARQ_BLOQUEADAS, "r", encoding="utf-8")
        for linha in arquivo:
            linha = linha.strip()
            if linha != "" and not linha.startswith("#"):
                bloqueadas.append(linha.upper())
        arquivo.close()
    except OSError:
        print("[ERRO] Não foi possível ler a lista de máquinas bloqueadas.")
    return bloqueadas


def contar_falhas_seguidas(matricula, acessos):
    contador = 0
    i = len(acessos) - 1
    while i >= 0:
        if acessos[i][A_MATRICULA] == matricula:
            if acessos[i][A_RESULTADO] != "falha":
                return contador
            contador += 1
        i -= 1
    return contador


def ultimo_acesso(matricula, acessos):
    i = len(acessos) - 1
    while i >= 0:
        if acessos[i][A_MATRICULA] == matricula:
            return acessos[i]
        i -= 1
    return []


def diferenca_minutos(data1, data2):
    try:
        d1 = datetime.strptime(data1, FORMATO_BANCO)
        d2 = datetime.strptime(data2, FORMATO_BANCO)
        return int((d2 - d1).total_seconds() / 60)
    except ValueError:
        return 9999


def avaliar_acesso(usuario, matricula, maquina, resultado, data_hora, acessos, bloqueadas):
    fatores = []
    hora = int(data_hora[11:13])
    if resultado == "falha":
        fatores.append([PESO_FALHA, "o acesso falhou"])
    if maquina in bloqueadas:
        fatores.append([PESO_MAQUINA_BLOQUEADA, f"máquina {maquina} está na lista de bloqueio"])
    if len(usuario) == 0:
        fatores.append([PESO_MATRICULA_DESCONHECIDA, "matrícula não cadastrada no sistema"])
    else:
        if usuario[U_BLOQUEADO] == "1":
            fatores.append([PESO_USUARIO_BLOQUEADO, "a conta deste usuário está bloqueada"])
        if not dentro_do_horario(hora, int(usuario[U_INICIO]), int(usuario[U_FIM])):
            fatores.append([PESO_FORA_HORARIO, f"fora do horário permitido ({usuario[U_INICIO]}h-{usuario[U_FIM]}h), "
                                               f"acesso às {data_hora[11:16]}"])
            if hora < 6:
                fatores.append([PESO_MADRUGADA, "madrugada (00h às 05h59): período de menor presença"])
            if resultado == "sucesso" and usuario[U_PERFIL] != "estudante":
                fatores.append([PESO_PERFIL, f"conta de {usuario[U_PERFIL]} (mais privilégios) aberta fora do horário"])
    if resultado == "falha":
        seguidas = contar_falhas_seguidas(matricula, acessos) + 1
        if seguidas >= LIMITE_FALHAS:
            fatores.append([PESO_FALHAS_SEGUIDAS, f"{seguidas} falhas seguidas desta matrícula"])
    anterior = ultimo_acesso(matricula, acessos)
    if len(anterior) > 0 and anterior[A_MAQUINA] != maquina:
        minutos = diferenca_minutos(anterior[A_DATA], data_hora)
        if 0 <= minutos <= JANELA_TROCA_MIN:
            fatores.append([PESO_TROCA_RAPIDA, f"mesma matrícula em {anterior[A_MAQUINA]} e {maquina} em {minutos} min"])
    pontos = 0
    motivos = ""
    for fator in fatores:
        pontos += fator[0]
        if motivos != "":
            motivos += " | "
        motivos += f"+{fator[0]} {fator[1]}"
    if motivos == "":
        motivos = "nenhum fator de risco encontrado"
    if pontos > 100:
        pontos = 100
    classe = "normal"
    if pontos >= LIMITE_CRITICO:
        classe = "crítico"
    elif pontos >= LIMITE_SUSPEITO:
        classe = "suspeito"
    return [pontos, classe, motivos]


def maquinas_compartilhadas(acessos, data=""):
    usos = []
    for a in acessos:
        if a[A_RESULTADO] == "sucesso" and a[A_DATA].startswith(data):
            achou = False
            for item in usos:
                if item[0] == a[A_MAQUINA]:
                    achou = True
                    if a[A_MATRICULA] not in item:
                        item.append(a[A_MATRICULA])
            if not achou:
                usos.append([a[A_MAQUINA], a[A_MATRICULA]])
    compartilhadas = []
    for item in usos:
        if len(item) > 2:
            compartilhadas.append(item)
    return compartilhadas


def registrar_acesso_direto(matricula, maquina, resultado, data_hora):
    usuarios = carregar_usuarios()
    posicao = buscar_usuario(matricula, usuarios)
    usuario = []
    if posicao != -1:
        usuario = usuarios[posicao]
    acessos = carregar_acessos()
    bloqueadas = carregar_maquinas_bloqueadas()
    avaliacao = avaliar_acesso(usuario, matricula, maquina, resultado, data_hora, acessos, bloqueadas)
    registro = [str(len(acessos) + 1), matricula, data_hora, maquina, resultado,
                avaliacao[1], str(avaliacao[0]), avaliacao[2]]
    if not anexar_linha_selada(ARQ_ACESSOS, registro):
        return [[], []]
    rotulo = rotulo_matricula(matricula, usuarios)
    registrar_auditoria("ACESSO_REGISTRADO", rotulo,
                        f"maquina={maquina}, resultado={resultado}, classe={avaliacao[1]}")
    alertas = []
    if maquina in bloqueadas:
        alertas.append(f"Acesso originado de máquina BLOQUEADA ({maquina}).")
    if resultado == "sucesso":
        acessos.append(registro)
        for item in maquinas_compartilhadas(acessos, data_hora[:10]):
            if item[0] == maquina:
                outros = []
                for outra in item[1:]:
                    if outra != matricula:
                        outros.append(rotulo_matricula(outra, usuarios))
                alertas.append(f"A máquina {maquina} também foi usada neste dia por: {', '.join(outros)}. "
                               "Fica difícil atribuir ações a uma só pessoa.")
    elif posicao != -1 and usuario[U_BLOQUEADO] == "0":
        seguidas = contar_falhas_seguidas(matricula, acessos) + 1
        if seguidas >= LIMITE_FALHAS:
            usuario[U_BLOQUEADO] = "1"
            if salvar_usuarios(usuarios):
                registrar_auditoria("USUARIO_BLOQUEADO_AUTO", rotulo, f"{seguidas} falhas seguidas")
                alertas.append(f"BLOQUEIO AUTOMÁTICO: {rotulo} teve {seguidas} falhas seguidas.")
    return [registro, alertas]


def mostrar_explicacao(registro):
    print(f"\n  Classificação: {registro[A_CLASSE].upper()} ({registro[A_PONTOS]}/100 pontos)")
    print("  Por quê:")
    for motivo in registro[A_MOTIVOS].split(" | "):
        print(f"    {motivo}")
    print(f"  Escala: normal < {LIMITE_SUSPEITO} | suspeito {LIMITE_SUSPEITO}-{LIMITE_CRITICO - 1} "
          f"| crítico >= {LIMITE_CRITICO}")


def registrar_acesso():
    if not exigir("acessos_registrar"):
        return
    print("\n--- Registrar acesso ---")
    matricula = ler_texto("  Matrícula do usuário: ", True, 12).upper()
    maquina = ler_texto("  Máquina de origem (ex.: PC-07): ", True, 20).upper()
    print("  Resultado: 1. sucesso   2. falha")
    resultado = "falha"
    if ler_inteiro("  Escolha: ", 1, 2) == 1:
        resultado = "sucesso"
    data_hora = ler_data_hora("  Data e hora [Enter = agora] (DD/MM/AAAA HH:MM): ")
    retorno = registrar_acesso_direto(matricula, maquina, resultado, data_hora)
    if len(retorno[0]) == 0:
        return
    print(f"\n  Acesso #{retorno[0][A_ID]} registrado.")
    mostrar_explicacao(retorno[0])
    for alerta in retorno[1]:
        print(f"  [ALERTA] {alerta}")


def listar_acessos(lista, usuarios):
    if len(lista) == 0:
        print("  Nenhum acesso encontrado.")
        return
    print(f"\n{'ID':>4}  {'Data/hora':<17}{'Usuário':<26}{'Máquina':<11}{'Resultado':<10}Classe")
    print("-" * 80)
    for a in lista:
        nome = rotulo_matricula(a[A_MATRICULA], usuarios)[:24]
        print(f"{a[A_ID]:>4}  {formatar_data(a[A_DATA]):<17}{nome:<26}{a[A_MAQUINA]:<11}"
              f"{a[A_RESULTADO]:<10}{a[A_CLASSE].upper()}")
    print(f"\n  {len(lista)} acesso(s) listado(s).")


def consultar_acessos():
    if not exigir("acessos_consultar"):
        return
    acessos = carregar_acessos()
    if len(acessos) == 0:
        print("  Nenhum acesso registrado ainda.")
        return
    usuarios = carregar_usuarios()
    opcao = escolher_opcao("CONSULTAR ACESSOS", ["Últimos 20 acessos", "Acessos de um usuário",
                                                 "Somente suspeitos e críticos", "Acessos de uma máquina"])
    lista = []
    if opcao == 1:
        lista = acessos[-20:]
    elif opcao == 2:
        posicao = selecionar_usuario(usuarios, "consultar")
        if posicao != -1:
            for a in acessos:
                if a[A_MATRICULA] == usuarios[posicao][U_MATRICULA]:
                    lista.append(a)
    elif opcao == 3:
        for a in acessos:
            if a[A_CLASSE] != "normal":
                lista.append(a)
    elif opcao == 4:
        maquina = ler_texto("  Máquina: ", True, 20).upper()
        for a in acessos:
            if a[A_MAQUINA] == maquina:
                lista.append(a)
    if opcao != 0:
        listar_acessos(lista, usuarios)


def explicar_acesso():
    if not exigir("acessos_explicar"):
        return
    acessos = carregar_acessos()
    if len(acessos) == 0:
        print("  Nenhum acesso registrado ainda.")
        return
    numero = ler_inteiro("  ID do acesso: ", 1, len(acessos))
    for a in acessos:
        if int(a[A_ID]) == numero:
            print(f"\n  Acesso #{numero}: {formatar_data(a[A_DATA])} em {a[A_MAQUINA]} ({a[A_RESULTADO]})")
            mostrar_explicacao(a)
            return
    print("  Não existe acesso com esse ID.")


def menu_acessos():
    while True:
        print("\n  (Acessos não podem ser editados nem excluídos: isso preserva o histórico.)")
        opcao = escolher_opcao_nivel("ACESSOS", [
            ["Registrar acesso", "acessos_registrar"],
            ["Consultar acessos", "acessos_consultar"],
            ["Explicar a classificação de um acesso", "acessos_explicar"],
        ])
        if opcao == 0:
            return
        elif opcao == 1:
            registrar_acesso()
        elif opcao == 2:
            consultar_acessos()
        elif opcao == 3:
            explicar_acesso()
        pausar()


def ver_maquinas_compartilhadas():
    if not exigir("deteccao_ver"):
        return
    usuarios = carregar_usuarios()
    compartilhadas = maquinas_compartilhadas(carregar_acessos())
    if len(compartilhadas) == 0:
        print("  Nenhuma máquina foi usada por mais de um usuário.")
    for item in compartilhadas:
        print(f"\n  [ALERTA] {item[0]} foi usada por {len(item) - 1} usuários:")
        for matricula in item[1:]:
            print(f"     - {rotulo_matricula(matricula, usuarios)}")


def bloquear_maquina():
    if not exigir("deteccao_bloquear_maquina"):
        return
    maquina = ler_texto("  Máquina/origem a bloquear: ", True, 20).upper()
    if maquina in carregar_maquinas_bloqueadas():
        print("  Essa máquina já está na lista.")
        return
    try:
        arquivo = open(ARQ_BLOQUEADAS, "a", encoding="utf-8")
        arquivo.write("\n" + maquina + "\n")
        arquivo.close()
        registrar_auditoria("MAQUINA_BLOQUEADA", "-", f"maquina={maquina}")
        print("  Máquina adicionada à lista de bloqueio.")
    except OSError:
        print("[ERRO] Não foi possível atualizar a lista de bloqueio.")


def menu_deteccao():
    while True:
        opcao = escolher_opcao_nivel("DETECÇÃO DE RISCO", [
            ["Máquinas usadas por mais de um usuário", "deteccao_ver"],
            ["Ver máquinas bloqueadas", "deteccao_ver"],
            ["Bloquear uma máquina/origem", "deteccao_bloquear_maquina"],
            ["Ver usuários bloqueados", "deteccao_ver"],
        ])
        if opcao == 0:
            return
        elif opcao == 1:
            ver_maquinas_compartilhadas()
        elif opcao == 2:
            if exigir("deteccao_ver"):
                print("  Máquinas/origens bloqueadas (maquinas_bloqueadas.txt):")
                for maquina in carregar_maquinas_bloqueadas():
                    print(f"     - {maquina}")
        elif opcao == 3:
            bloquear_maquina()
        elif opcao == 4:
            if exigir("deteccao_ver"):
                usuarios = carregar_usuarios()
                achou = False
                for u in usuarios:
                    if u[U_BLOQUEADO] == "1":
                        print(f"     - {rotulo_matricula(u[U_MATRICULA], usuarios)}")
                        achou = True
                if not achou:
                    print("  Nenhum usuário bloqueado no momento.")
        pausar()


def verificar_cadeia(caminho):
    anterior = SELO_INICIAL
    linhas = ler_linhas(caminho)
    for i in range(len(linhas)):
        conteudo = SEPARADOR.join(linhas[i][:-1])
        if calcular_selo(anterior + "|" + conteudo) != linhas[i][-1]:
            return i + 1
        anterior = linhas[i][-1]
    return 0


def contar_em(pares, chave):
    for par in pares:
        if par[1] == chave:
            par[0] = par[0] + 1
            return
    pares.append([1, chave])


def contar_por_hora(acessos):
    contagem = [0] * 24
    for a in acessos:
        hora = int(a[A_DATA][11:13])
        contagem[hora] += 1
    return contagem


def grafico_por_hora(acessos):
    contagem = contar_por_hora(acessos)
    maior = max(contagem)
    if maior == 0:
        maior = 1
    linhas = []
    for hora in range(24):
        barra = "#" * int(contagem[hora] * 30 / maior + 0.5)
        aviso = ""
        if contagem[hora] > 0 and (hora < 7 or hora >= 22):
            aviso = "  <-- laboratório fechado!"
        linhas.append(f"  {hora:02d}h | {barra} {contagem[hora]}{aviso}")
    return linhas


def gerar_relatorio():
    acessos = carregar_acessos()
    usuarios = carregar_usuarios()
    falhas = 0
    suspeitos = 0
    criticos = 0
    falhas_por_matricula = []
    for a in acessos:
        if a[A_RESULTADO] == "falha":
            falhas += 1
            contar_em(falhas_por_matricula, a[A_MATRICULA])
        if a[A_CLASSE] == "suspeito":
            suspeitos += 1
        elif a[A_CLASSE] == "crítico":
            criticos += 1
    bloqueados = 0
    for u in usuarios:
        if u[U_BLOQUEADO] == "1":
            bloqueados += 1
    taxa = 0
    if len(acessos) > 0:
        taxa = falhas / len(acessos) * 100
    linhas = ["=" * 62, "RELATÓRIO DE SEGURANÇA - SENTINELALOG".center(62), "=" * 62,
              f"Acessos registrados : {len(acessos)}",
              f"Acessos com falha   : {falhas} ({taxa:.1f}%)",
              f"Acessos suspeitos   : {suspeitos}",
              f"Acessos críticos    : {criticos}",
              f"Usuários cadastrados: {len(usuarios)} ({bloqueados} bloqueado(s))",
              "", "Usuários que concentram mais falhas:"]
    falhas_por_matricula.sort(reverse=True)
    if len(falhas_por_matricula) == 0:
        linhas.append("  (nenhuma falha registrada)")
    for par in falhas_por_matricula[:5]:
        linhas.append(f"  {par[0]:>3} falha(s)  {rotulo_matricula(par[1], usuarios)}")
    linhas.append("")
    linhas.append("Horários com mais movimento:")
    contagem = contar_por_hora(acessos)
    horas = []
    for hora in range(24):
        if contagem[hora] > 0:
            horas.append([contagem[hora], hora])
    horas.sort(reverse=True)
    if len(horas) == 0:
        linhas.append("  (sem movimento registrado)")
    for par in horas[:3]:
        linhas.append(f"  {par[1]:02d}h: {par[0]} acesso(s)")
    linhas.append("")
    linhas.append("Movimento por hora:")
    linhas = linhas + grafico_por_hora(acessos)
    linhas.append("")
    compartilhadas = maquinas_compartilhadas(acessos)
    linhas.append(f"Máquinas usadas por mais de um usuário: {len(compartilhadas)}")
    for item in compartilhadas:
        linhas.append(f"  {item[0]}: {len(item) - 1} usuários")
    linhas.append("")
    if verificar_cadeia(ARQ_ACESSOS) == 0 and verificar_cadeia(ARQ_AUDITORIA) == 0:
        linhas.append("Integridade dos registros: OK (nenhuma adulteração detectada)")
    else:
        linhas.append("Integridade dos registros: ALERTA! Há arquivo adulterado (veja o Radar Sentinela).")
    return linhas


def mostrar_relatorio():
    if not exigir("relatorio"):
        return
    registrar_auditoria("RELATORIO_CONSULTADO")
    for linha in gerar_relatorio():
        print(linha)


USUARIOS_DEMO = [
    ["20260001", "Alice Souza", "estudante", "7", "18", "fictício (simulação)", "0"],
    ["20260002", "Bruno Lima", "estudante", "7", "22", "fictício (simulação)", "0"],
    ["20260003", "Carla Mendes", "estudante", "14", "22", "fictício (simulação)", "0"],
    ["PROF001", "Davi Rocha", "professor", "7", "22", "fictício (simulação)", "0"],
    ["PROF002", "Elisa Ramos", "professor", "7", "18", "fictício (simulação)", "0"],
    ["ADM001", "Fabio Nunes", "administrador", "7", "22", "fictício (simulação)", "0"],
]


def calcular_score(matricula, acessos):
    score = 0
    for a in acessos:
        if a[A_MATRICULA] == matricula:
            if a[A_CLASSE] == "crítico":
                score += 25
            elif a[A_CLASSE] == "suspeito":
                score += 10
            if a[A_RESULTADO] == "falha":
                score += 3
    if score > 100:
        score = 100
    return score


def nivel_do_score(score):
    if score >= 60:
        return "ALTO"
    elif score >= 25:
        return "MÉDIO"
    return "baixo"


def mostrar_ranking():
    if not exigir("extra_consultar"):
        return
    acessos = carregar_acessos()
    usuarios = carregar_usuarios()
    ranking = []
    matriculas = []
    for a in acessos:
        if a[A_MATRICULA] not in matriculas:
            matriculas.append(a[A_MATRICULA])
            ranking.append([calcular_score(a[A_MATRICULA], acessos), a[A_MATRICULA]])
    if len(ranking) == 0:
        print("  Ainda não há acessos para calcular o risco.")
        return
    ranking.sort(reverse=True)
    print("\n  RANKING DE RISCO (0 a 100)")
    print("  Nota = críticos x25 + suspeitos x10 + falhas x3\n")
    for par in ranking[:10]:
        barra = "#" * (par[0] // 5) + "." * (20 - par[0] // 5)
        print(f"  [{barra}] {par[0]:>3}  {nivel_do_score(par[0]):<6} {rotulo_matricula(par[1], usuarios)}")


def investigar_usuario():
    if not exigir("extra_consultar"):
        return
    usuarios = carregar_usuarios()
    posicao = selecionar_usuario(usuarios, "investigar")
    if posicao == -1:
        return
    u = usuarios[posicao]
    acessos = carregar_acessos()
    dele = []
    for a in acessos:
        if a[A_MATRICULA] == u[U_MATRICULA]:
            dele.append(a)
    score = calcular_score(u[U_MATRICULA], acessos)
    registrar_auditoria("INVESTIGACAO", rotulo_matricula(u[U_MATRICULA], usuarios))
    print("\n" + "=" * 62)
    print(f"  INVESTIGAÇÃO: {rotulo_matricula(u[U_MATRICULA], usuarios)}")
    print("=" * 62)
    status = "ativo"
    if u[U_BLOQUEADO] == "1":
        status = "BLOQUEADO"
    print(f"  Perfil: {u[U_PERFIL]} | Horário permitido: {u[U_INICIO]}h-{u[U_FIM]}h | Status: {status}")
    print(f"  Nota de risco: {score}/100 ({nivel_do_score(score)})")
    if len(dele) == 0:
        print("\n  Esta conta ainda não tem acessos registrados.")
        return
    print("\n  1) QUEM? Linha do tempo (últimos 10 acessos)")
    listar_acessos(dele[-10:], usuarios)
    print("\n  2) DE ONDE VEIO? Máquinas usadas por esta conta")
    bloqueadas = carregar_maquinas_bloqueadas()
    compartilhadas = maquinas_compartilhadas(acessos)
    maquinas = []
    for a in dele:
        if a[A_MAQUINA] not in maquinas:
            maquinas.append(a[A_MAQUINA])
    for maquina in maquinas:
        sucessos = 0
        falhas = 0
        for a in dele:
            if a[A_MAQUINA] == maquina:
                if a[A_RESULTADO] == "sucesso":
                    sucessos += 1
                else:
                    falhas += 1
        avisos = ""
        if maquina in bloqueadas:
            avisos += "  [BLOQUEADA]"
        for item in compartilhadas:
            if item[0] == maquina:
                avisos += "  [usada por vários usuários]"
        print(f"     {maquina:<10} {sucessos} sucesso(s), {falhas} falha(s){avisos}")
    print("\n  3) JÁ ACONTECEU ANTES?")
    ocorrencias = []
    for a in dele:
        if a[A_CLASSE] != "normal":
            ocorrencias.append(a)
    if len(ocorrencias) == 0:
        print("     Nenhuma ocorrência suspeita ou crítica anterior.")
    else:
        print(f"     {len(ocorrencias)} ocorrência(s) suspeita(s) ou crítica(s).")
        print(f"     Primeira: {formatar_data(ocorrencias[0][A_DATA])} em {ocorrencias[0][A_MAQUINA]}")
        print(f"     Mais recente: {formatar_data(ocorrencias[-1][A_DATA])} em {ocorrencias[-1][A_MAQUINA]}")
        print(f"     Principal motivo da mais recente: {ocorrencias[-1][A_MOTIVOS].split(' | ')[0]}")


def verificar_integridade():
    if not exigir("extra_consultar"):
        return
    print("  Verificando selos de integridade...\n")
    for caminho in [ARQ_ACESSOS, ARQ_AUDITORIA]:
        nome = os.path.basename(caminho)
        linha = verificar_cadeia(caminho)
        if linha == 0:
            print(f"  [OK]     {nome}: cadeia íntegra ({len(ler_linhas(caminho))} linhas).")
        else:
            print(f"  [ALERTA] {nome}: a cadeia quebrou na linha {linha}. O arquivo foi alterado fora do sistema!")


def explicar_selos():
    print("""
  COMO FUNCIONA O SELO DE INTEGRIDADE
  Cada linha de acessos.csv e auditoria.csv termina com um selo calculado a
  partir do conteúdo da linha + o selo da linha anterior (como uma corrente).
  Se alguém editar ou apagar uma linha do meio, os selos seguintes não batem.

  O QUE O SELO NÃO DETECTA (ótimo para a apresentação):
   - Apagar as ÚLTIMAS linhas ou o arquivo inteiro.
   - Quem conhece o cálculo e refaz toda a cadeia depois de editar.
   - O selo é uma checagem simples, não é criptografia forte.""")


def criar_usuarios_demo():
    if not exigir("extra_simular"):
        return
    usuarios = carregar_usuarios()
    criados = 0
    for demo in USUARIOS_DEMO:
        if buscar_usuario(demo[U_MATRICULA], usuarios) == -1:
            usuarios.append(list(demo))
            criados += 1
    if salvar_usuarios(usuarios):
        registrar_auditoria("SIMULACAO_USUARIOS", "-", f"{criados} usuário(s) fictício(s)")
    print(f"  {criados} usuário(s) fictício(s) criado(s).")


def gerar_acessos_aleatorios():
    if not exigir("extra_simular"):
        return
    usuarios = carregar_usuarios()
    if len(usuarios) == 0:
        print("  Cadastre usuários antes (ou crie os usuários fictícios).")
        return
    quantidade = ler_inteiro("  Quantos acessos gerar? (1-200): ", 1, 200)
    eventos = []
    for i in range(quantidade):
        u = random.choice(usuarios)
        dia = datetime.now() - timedelta(days=random.randint(1, 7))
        permitidas = []
        for h in range(24):
            if dentro_do_horario(h, int(u[U_INICIO]), int(u[U_FIM])):
                permitidas.append(h)
        hora = random.randint(0, 23)
        if random.random() < 0.85 and len(permitidas) > 0:
            hora = random.choice(permitidas)
        data_hora = dia.replace(hour=hora, minute=random.randint(0, 59)).strftime(FORMATO_BANCO)
        maquina = f"PC-{random.randint(1, 30):02d}"
        if random.random() < 0.03:
            maquina = random.choice(["PC-99", "REMOTO-01"])
        resultado = "sucesso"
        if random.random() < 0.10:
            resultado = "falha"
        eventos.append([data_hora, u[U_MATRICULA], maquina, resultado])
    eventos.sort()
    normais = 0
    suspeitos = 0
    criticos = 0
    bloqueios = 0
    for e in eventos:
        retorno = registrar_acesso_direto(e[1], e[2], e[3], e[0])
        if len(retorno[0]) > 0 and retorno[0][A_CLASSE] == "normal":
            normais += 1
        elif len(retorno[0]) > 0 and retorno[0][A_CLASSE] == "suspeito":
            suspeitos += 1
        elif len(retorno[0]) > 0:
            criticos += 1
        for alerta in retorno[1]:
            if alerta.startswith("BLOQUEIO AUTOMÁTICO"):
                bloqueios += 1
    registrar_auditoria("SIMULACAO_ACESSOS", "-", f"{quantidade} acesso(s) aleatório(s)")
    print(f"\n  Gerados: {normais} normais, {suspeitos} suspeitos, {criticos} críticos. "
          f"Bloqueios automáticos: {bloqueios}.")


def incidente_das_3h():
    if not exigir("extra_simular"):
        return
    print("\n  INCIDENTE DAS 3H - reconstituição com dados fictícios")
    criar_usuarios_demo()
    historia = [
        [2, "08:05", "PC-05", "sucesso", "Rotina: o professor entra normalmente."],
        [2, "10:30", "PC-05", "sucesso", "Rotina: segunda sessão do dia."],
        [1, "03:10", "PC-27", "falha", "Madrugada: alguém tenta a conta do professor."],
        [1, "03:11", "PC-27", "falha", "Segunda tentativa."],
        [1, "03:12", "PC-27", "falha", "Terceira tentativa seguida."],
        [1, "03:14", "PC-27", "sucesso", "A conta é aberta. Era aqui que os arquivos eram apagados."],
    ]
    for passo in historia:
        dia = (datetime.now() - timedelta(days=passo[0])).strftime("%Y-%m-%d")
        retorno = registrar_acesso_direto("PROF001", passo[2], passo[3], dia + " " + passo[1])
        registro = retorno[0]
        if len(registro) > 0:
            print(f"\n  {formatar_data(registro[A_DATA])} | {passo[2]} | {passo[3]} -> "
                  f"{registro[A_CLASSE].upper()} ({registro[A_PONTOS]} pts)")
            print(f"     {passo[4]}")
            for alerta in retorno[1]:
                print(f"     [ALERTA PARA A ANA] {alerta}")
    registrar_auditoria("SIMULACAO_INCIDENTE", "-", "incidente das 3h reproduzido")
    print("\n  Conclusão: a Ana seria avisada já na primeira tentativa (03:10), mesmo sem lista de")
    print("  bloqueio, só pelo horário, pela madrugada e pela sequência de falhas.")
    print("  (O professor fictício ficou bloqueado: libere em Usuários > Bloquear/desbloquear.)")


def menu_simulador():
    while True:
        opcao = escolher_opcao("SIMULADOR (dados fictícios)", ["Criar usuários fictícios",
                                                               "Gerar acessos aleatórios",
                                                               "Reproduzir o Incidente das 3h"])
        if opcao == 0:
            return
        elif opcao == 1:
            criar_usuarios_demo()
        elif opcao == 2 and confirmar("  Isso grava acessos fictícios nos arquivos. Continuar?"):
            gerar_acessos_aleatorios()
        elif opcao == 3 and confirmar("  Isso grava acessos fictícios nos arquivos. Continuar?"):
            incidente_das_3h()
        pausar()


def exportar_relatorio():
    if not exigir("extra_exportar"):
        return
    nome = "relatorio_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"
    try:
        arquivo = open(os.path.join(PASTA_DADOS, nome), "w", encoding="utf-8")
        for linha in gerar_relatorio():
            arquivo.write(linha + "\n")
        arquivo.close()
        registrar_auditoria("RELATORIO_EXPORTADO", "-", nome)
        print(f"  Relatório salvo em dados/{nome}")
    except OSError:
        print("[ERRO] Não foi possível exportar o relatório.")


def menu_radar():
    while True:
        opcao = escolher_opcao_nivel("RADAR SENTINELA (extra)", [
            ["Ranking de risco por usuário", "extra_consultar"],
            ["Modo Investigação (quem? de onde? já aconteceu antes?)", "extra_consultar"],
            ["Verificar integridade dos registros (selos)", "extra_consultar"],
            ["Entender o selo de integridade", "extra_consultar"],
            ["Simulador de acessos e incidentes (dados fictícios)", "extra_simular"],
            ["Exportar relatório para arquivo .txt", "extra_exportar"],
        ])
        if opcao == 0:
            return
        elif opcao == 5:
            menu_simulador()
        else:
            if opcao == 1:
                mostrar_ranking()
            elif opcao == 2:
                investigar_usuario()
            elif opcao == 3:
                verificar_integridade()
            elif opcao == 4:
                explicar_selos()
            elif opcao == 6:
                exportar_relatorio()
            pausar()


def perguntar_ia():
    if IA is None:
        print("  O módulo de IA (IA.py) não foi encontrado nesta pasta.")
        return
    pergunta = input("  Pergunte algo pra IA: ")
    print(IA.perguntar_ia(pergunta))


def menu_principal():
    while True:
        print(f"\n  Operador: {SESSAO[S_LOGIN]} | Nível: {nome_nivel(SESSAO[S_NIVEL])}")
        opcao = escolher_opcao_nivel("SENTINELALOG - MENU PRINCIPAL", [
            ["Usuários", "usuarios_listar"],
            ["Acessos", "acessos_consultar"],
            ["Detecção de risco", "deteccao_ver"],
            ["Auditoria (consultar log)", "auditoria_consultar"],
            ["Relatório de segurança", "relatorio"],
            ["Radar Sentinela (extra)", "extra_consultar"],
            ["Assistente de IA", "ia"],
            ["Operadores (contas e níveis)", "operadores_gerenciar"],
            ["Minha conta (senha e permissões)", "conta_propria"],
        ], "Sair")
        if opcao == 0:
            return
        elif opcao == 1:
            menu_usuarios()
        elif opcao == 2:
            menu_acessos()
        elif opcao == 3:
            menu_deteccao()
        elif opcao == 6:
            menu_radar()
        elif opcao == 8:
            menu_operadores()
        elif opcao == 9:
            menu_minha_conta()
        else:
            if opcao == 4:
                consultar_auditoria()
            elif opcao == 5:
                mostrar_relatorio()
            elif opcao == 7:
                if exigir("ia"):
                    perguntar_ia()
            pausar()


def main():
    mostrar_titulo("SENTINELALOG - Monitor de Acessos")
    print("  Sistema didático: use apenas dados fictícios.\n")
    if not preparar_arquivos():
        return
    if not garantir_superadmin_fixo():
        return
    try:
        if not autenticar():
            return
        registrar_auditoria("SESSAO_INICIADA", "-", f"nivel={nome_nivel(SESSAO[S_NIVEL])}")
        menu_principal()
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Encerrando por interrupção do usuário.")
    registrar_auditoria("SESSAO_ENCERRADA")
    print("  Até logo!")


if __name__ == "__main__":
    main()
