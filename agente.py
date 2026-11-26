"""Assistente de Agendamento — Oficina Mecânica Auto Fácil.

Protótipo de agente de IA executado no terminal usando Python e Ollama
(modelo local gratuito qwen2.5:3b) para interpretar pedidos de horário,
consultar horários livres em uma ferramenta simulada, validar a disponibilidade
e exigir confirmação humana antes de salvar em arquivo.
"""

from datetime import datetime
import re
import ollama

# ==============================================================================
# CONFIGURAÇÕES DO AGENTE
# ==============================================================================
# Nome do modelo local gratuito baixado no Ollama (licença Apache 2.0)
MODELO = "qwen2.5:3b"

# Quantidade máxima de tentativas permitidas ao cliente antes de encerrar
MAX_TENTATIVAS = 3

# Nome do arquivo de texto onde os agendamentos confirmados serão salvos
ARQUIVO_AGENDAMENTOS = "agendamentos.txt"


# ==============================================================================
# FERRAMENTA SIMULADA (RQ02)
# ==============================================================================
def ver_horarios_livres() -> list[str]:
    """Simula a consulta à agenda da oficina e devolve os horários livres.

    Em um sistema real, esta função consultaria um banco de dados ou API.
    Neste protótipo, retorna uma lista fixa de horários disponíveis.
    """
    return ["08h", "10h", "14h", "16h"]


# ==============================================================================
# NORMALIZAÇÃO E INTERPRETAÇÃO VIA LLM (RQ01)
# ==============================================================================
def normalizar_horario(resposta_llm: str) -> str | None:
    """Padroniza a resposta retornada pelo LLM para o formato 'HHh' (ex.: '08h', '14h').

    Esta função trata apenas o texto produzido pelo modelo de IA (nunca lê a
    mensagem bruta do cliente diretamente) para remover pontuação ou espaços extras.
    Retorna None caso o modelo indique 'NENHUM' ou não haja dígitos na resposta.
    """
    if not resposta_llm:
        return None

    texto = resposta_llm.strip()
    if "NENHUM" in texto.upper():
        return None

    # Procura um número de hora na resposta do LLM (ex.: '8h', '14:00', '9 horas')
    correspondencia = re.search(r"\b(\d{1,2})\s*(?:h|hs|horas|:00)?\b", texto, re.IGNORECASE)
    if not correspondencia:
        return None

    hora = int(correspondencia.group(1))
    # Formata sempre com dois dígitos seguidos de 'h' (ex.: 9 -> '09h', 14 -> '14h')
    return f"{hora:02d}h"


def extrair_horario_com_llm(mensagem_cliente: str) -> str | None:
    """Envia a mensagem do cliente ao LLM local para identificar o horário pedido.

    Utiliza temperatura 0 e exemplos (few-shot) no prompt de sistema para que o
    modelo responda somente com o horário no formato 'HHh' ou 'NENHUM'.
    """
    prompt_sistema = (
        "Você é um assistente da Oficina Mecânica Auto Fácil.\n"
        "Sua única tarefa é identificar o horário pedido na mensagem do cliente.\n"
        "Regras obrigatórias:\n"
        "1. Responda APENAS o horário no formato 24h com dois dígitos e 'h' (ex.: 08h, 09h, 14h).\n"
        "2. Converta expressões faladas para 24h (ex.: 'duas da tarde' -> 14h, 'oito da manhã' -> 08h).\n"
        "3. Se o cliente não citar nenhum horário, responda APENAS: NENHUM\n"
        "4. Não escreva explicações, saudações nem frases completas.\n\n"
        "Exemplos:\n"
        "Cliente: Quero marcar uma revisão às 14h -> 14h\n"
        "Cliente: Pode ser às 9 horas? -> 09h\n"
        "Cliente: Gostaria de agendar para as 10:00 -> 10h\n"
        "Cliente: Quero revisão às duas da tarde -> 14h\n"
        "Cliente: Tem vaga oito da manhã? -> 08h\n"
        "Cliente: Olá, tudo bem? -> NENHUM"
    )

    try:
        # Chamada ao modelo local rodando via Ollama (sem internet e sem chave de API)
        resposta = ollama.chat(
            model=MODELO,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": mensagem_cliente},
            ],
            options={"temperature": 0},
        )
    except Exception as erro:
        raise RuntimeError(
            "Não foi possível se comunicar com o Ollama.\n"
            f"Verifique se o serviço do Ollama está ativo e se o modelo '{MODELO}' foi baixado "
            f"com o comando: ollama pull {MODELO}"
        ) from erro

    conteudo = resposta["message"]["content"]
    return normalizar_horario(conteudo)


# ==============================================================================
# CONFIRMAÇÃO HUMANA E PERSISTÊNCIA (RQ04)
# ==============================================================================
def solicitar_confirmacao_humana(mensagem_cliente: str, horario: str) -> bool:
    """Exibe o resumo do agendamento e pede confirmação (S/N) à equipe da oficina.

    Só retorna True se o atendente digitar exatamente 'S' (maiúsculo ou minúsculo).
    """
    print("\n" + "-" * 45)
    print("RESUMO DO AGENDAMENTO")
    print("-" * 45)
    print("Oficina: Auto Fácil")
    print(f"Mensagem do cliente: {mensagem_cliente}")
    print(f"Horário solicitado: {horario}")
    print("-" * 45)

    while True:
        decisao = input("Confirmar agendamento? (S/N): ").strip().upper()
        if decisao == "S":
            return True
        if decisao == "N":
            return False
        print("Resposta inválida. Por favor, digite apenas S para confirmar ou N para cancelar.")


def salvar_agendamento(mensagem_cliente: str, horario: str) -> None:
    """Grava o agendamento confirmado no final do arquivo agendamentos.txt."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    linha = f"[{agora}] Horário: {horario} | Pedido: {mensagem_cliente}\n"

    # Abre o arquivo em modo 'a' (append) para preservar agendamentos anteriores
    with open(ARQUIVO_AGENDAMENTOS, "a", encoding="utf-8") as arquivo:
        arquivo.write(linha)


# ==============================================================================
# FLUXO PRINCIPAL E CONTROLE DE EXECUÇÃO (RQ03 e RQ05)
# ==============================================================================
def executar_agente() -> None:
    """Coordena o atendimento no terminal com limite de 3 tentativas."""
    print("=" * 55)
    print("  OFICINA MECÂNICA AUTO FÁCIL - ASSISTENTE DE REVISÃO")
    print("=" * 55)
    print("Bem-vindo! Informe o pedido do cliente para verificar a agenda.\n")

    # Loop controlado para garantir no máximo MAX_TENTATIVAS (3) tentativas
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        mensagem = input(f"[Tentativa {tentativa}/{MAX_TENTATIVAS}] Digite a mensagem do cliente: ").strip()

        # Consulta a ferramenta simulada para obter os horários livres atuais
        horarios_livres = ver_horarios_livres()
        lista_formatada = ", ".join(horarios_livres)

        # Validação básica para mensagem vazia
        if not mensagem:
            print(
                "Mensagem vazia. Por favor, descreva o pedido com um horário.\n"
                f"Horários livres disponíveis: {lista_formatada}\n"
            )
            continue

        # Etapa 1 do fluxo: usar o LLM para extrair o horário pedido
        horario_pedido = extrair_horario_com_llm(mensagem)

        if horario_pedido is None:
            print(
                "Não consegui identificar um horário na sua mensagem.\n"
                f"Por favor, informe um dos horários livres: {lista_formatada}\n"
            )
            continue

        print(f"Horário identificado pela IA: {horario_pedido}")

        # Etapa 2 do fluxo: validar se o horário identificado existe na lista livre (RQ03)
        if horario_pedido not in horarios_livres:
            print(
                f"Desculpe, o horário {horario_pedido} está ocupado ou não existe na agenda.\n"
                f"Horários livres disponíveis: {lista_formatada}\n"
            )
            continue

        # Etapa 3 do fluxo: horário válido encontrado -> solicitar confirmação humana (RQ04)
        print(f"Ótima notícia! O horário {horario_pedido} está livre.")
        confirmado = solicitar_confirmacao_humana(mensagem, horario_pedido)

        if confirmado:
            salvar_agendamento(mensagem, horario_pedido)
            print(
                f"\nAgendamento para as {horario_pedido} confirmado e salvo com sucesso "
                f"em '{ARQUIVO_AGENDAMENTOS}'!"
            )
        else:
            print("\nAgendamento cancelado pela equipe. Nenhum registro foi salvo.")

        # Encerra após a decisão humana (confirmado ou cancelado)
        return

    # Mensagem educada caso todas as 3 tentativas tenham falhado (RQ05)
    print(
        "\nVocê atingiu o limite máximo de 3 tentativas.\n"
        "Para continuar, entre em contato diretamente com a equipe da Oficina Auto Fácil. "
        "Obrigado pela compreensão!"
    )


if __name__ == "__main__":
    # Tratamento amigável de erros para evitar mensagens técnicas no terminal
    try:
        executar_agente()
    except RuntimeError as erro_ia:
        print(f"\n[Erro de configuração] {erro_ia}")
    except (KeyboardInterrupt, EOFError):
        print("\n\nAtendimento encerrado pelo usuário. Até logo!")
