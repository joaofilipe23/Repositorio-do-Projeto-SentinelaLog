import os
from datetime import datetime
import IA
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
def limpar_campo(texto):
    return str(texto).replace(SEPARADOR, ",").replace("\n", " ").replace("\r", " ").strip()
def preparar_arquivos():
    try:
        os.makedirs(PASTA_DADOS, exist_ok=True)
        for caminho in [ARQ_USUARIOS, ARQ_ACESSOS, ARQ_AUDITORIA]:
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
    usuarios = carregar_usuarios()
    posicao = selecionar_usuario(usuarios, "revelar a matrícula")
    if posicao == -1:
        return
    u = usuarios[posicao]
    motivo = ler_texto("  Motivo da consulta (obrigatório): ", True, 80)
    print(f"\n  Matrícula de {u[U_NOME]}: {u[U_MATRICULA]}")
    registrar_auditoria("MATRICULA_REVELADA", rotulo_matricula(u[U_MATRICULA], usuarios), f"motivo={motivo}")
def alternar_bloqueio():
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
        opcao = escolher_opcao("USUÁRIOS", [
            "Adicionar usuário",
            "Listar usuários (matrícula mascarada)",
            "Editar usuário",
            "Excluir usuário",
            "Revelar matrícula (fica no log)",
            "Bloquear / desbloquear usuário",
        ])
        if opcao == 0:
            return
        elif opcao == 1:
            adicionar_usuario()
        elif opcao == 2:
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
        elif opcao == 7:
            pergunta = input("  Pergunte algo pra IA: ")
            print(IA.perguntar_IA(pergunta))
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
        opcao = escolher_opcao("ACESSOS", ["Registrar acesso", "Consultar acessos",
                                           "Explicar a classificação de um acesso"])
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
    usuarios = carregar_usuarios()
    compartilhadas = maquinas_compartilhadas(carregar_acessos())
    if len(compartilhadas) == 0:
        print("  Nenhuma máquina foi usada por mais de um usuário.")
    for item in compartilhadas:
        print(f"\n  [ALERTA] {item[0]} foi usada por {len(item) - 1} usuários:")
        for matricula in item[1:]:
            print(f"     - {rotulo_matricula(matricula, usuarios)}")
def bloquear_maquina():
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
        opcao = escolher_opcao("DETECÇÃO DE RISCO", [
            "Máquinas usadas por mais de um usuário",
            "Ver máquinas bloqueadas",
            "Bloquear uma máquina/origem",
            "Ver usuários bloqueados",
        ])
        if opcao == 0:
            return
        elif opcao == 1:
            ver_maquinas_compartilhadas()
        elif opcao == 2:
            print("  Máquinas/origens bloqueadas (maquinas_bloqueadas.txt):")
            for maquina in carregar_maquinas_bloqueadas():
                print(f"     - {maquina}")
        elif opcao == 3:
            bloquear_maquina()
        elif opcao == 4:
            usuarios = carregar_usuarios()
            achou = False
            for u in usuarios:
                if u[U_BLOQUEADO] == "1":
                    print(f"     - {rotulo_matricula(u[U_MATRICULA], usuarios)}")
                    achou = True
            if not achou:
                print("  Nenhum usuário bloqueado no momento.")
        pausar()
def em_desenvolvimento(nome):
    print(f"\n  '{nome}' está em desenvolvimento e estará na entrega final.")
def menu_principal():
    while True:
        opcao = escolher_opcao("SENTINELALOG (PARCIAL) - MENU PRINCIPAL", [
            "Usuários",
            "Acessos",
            "Detecção de risco",
            "Auditoria (consultar log)",
            "Relatório de segurança (em desenvolvimento)",
            "Funcionalidade extra (em desenvolvimento)",
            "Assistente de IA (reservado)",
        ], "Sair")
        if opcao == 0:
            return
        elif opcao == 1:
            menu_usuarios()
        elif opcao == 2:
            menu_acessos()
        elif opcao == 3:
            menu_deteccao()
        else:
            if opcao == 4:
                consultar_auditoria()
            elif opcao == 5:
                em_desenvolvimento("Relatório de segurança")
            elif opcao == 6:
                em_desenvolvimento("Funcionalidade extra")
            elif opcao == 7:
                pergunta = input("  Pergunte algo pra IA: ")
                print(IA.perguntar_ia(pergunta))
            pausar()
def main():
    mostrar_titulo("SENTINELALOG - Monitor de Acessos (PARCIAL)")
    print("  Sistema didático: use apenas dados fictícios.\n")
    if not preparar_arquivos():
        return
    try:
        OPERADOR[0] = ler_texto("  Identifique-se (nome do operador): ", True, 30)
        registrar_auditoria("SESSAO_INICIADA")
        menu_principal()
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Encerrando por interrupção do usuário.")
    registrar_auditoria("SESSAO_ENCERRADA")
    print("  Até logo!")
if __name__ == "__main__":
    main()
