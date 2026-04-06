import sys
from models import STAKEHOLDERS, SALAS, DIAS_SEMANA, SLOT_DURACAO_MIN, slot_para_hora
from solver import AgendaSolver
from models import Reuniao

_contador_id = 0

def proximo_id():
    global _contador_id
    _contador_id += 1
    return _contador_id


def ler_inteiro(prompt, minimo, maximo):
    while True:
        try:
            valor = int(input(f"  {prompt}: "))
            if minimo <= valor <= maximo:
                return valor
            print(f"  Erro: Digite um numero entre {minimo} e {maximo}.")
        except ValueError:
            print("  Erro: Entrada invalida.")


def nova_reuniao(solver):
    print("\n--- NOVA REUNIAO ---")

    # Escolha do stakeholder
    print("\nStakeholders disponiveis:")
    for i, s in enumerate(STAKEHOLDERS, 1):
        print(f"  [{i}] {s['nome']} | {s['num_pessoas']} pessoas | prioridade {s['prioridade']}/5")
    idx = ler_inteiro("Selecione o stakeholder", 1, len(STAKEHOLDERS))
    stakeholder = STAKEHOLDERS[idx - 1]

    # Pessoas extras
    max_extras = max(s["capacidade"] for s in SALAS) - stakeholder["num_pessoas"]
    max_extras = max(0, max_extras)
    extras = ler_inteiro(f"Quantas pessoas extras (0-{max_extras})", 0, max_extras)

    # Duracao
    print("\nDuracao (slots de 30 min):")
    for i in range(1, 9):
        print(f"  [{i}] {i * 0.5:.1f}h")
    duracao = ler_inteiro("Selecione a duracao", 1, 8)

    # Dias possiveis
    print("\nDias possiveis (ex: 1,3,5):")
    for k, nome in DIAS_SEMANA.items():
        print(f"  [{k + 1}] {nome}")
    while True:
        entrada = input("  Dias: ").strip()
        try:
            dias = list(set(int(x.strip()) - 1 for x in entrada.split(",")))
            if all(0 <= d <= 4 for d in dias) and len(dias) > 0:
                break
            print("  Erro: Use numeros de 1 a 5.")
        except ValueError:
            print("  Erro: Formato invalido. Ex: 1,3,5")

    # Confirmacao
    total = stakeholder["num_pessoas"] + extras
    horas = duracao * SLOT_DURACAO_MIN / 60
    dias_str = ", ".join(DIAS_SEMANA[d] for d in sorted(dias))
    print(f"\n  Stakeholder : {stakeholder['nome']}")
    print(f"  Participantes: {total} pessoas")
    print(f"  Duracao     : {horas:.1f}h")
    print(f"  Dias        : {dias_str}")

    conf = input("  Confirmar? (s/n): ").strip().lower()
    if conf != "s":
        print("  Cancelado.")
        return

    reuniao = Reuniao(
        id=proximo_id(),
        stakeholder=stakeholder,
        extras=extras,
        duracao_slots=duracao,
        dias_possiveis=sorted(dias),
    )

    sucesso = solver.agendar(reuniao)

    if sucesso:
        print(f"\n  Reuniao agendada: {reuniao.descricao()}")
        return

    print("\n  Nenhum horario disponivel nos dias selecionados.")
    candidata = solver.sugerir_remanejamento(reuniao)

    if candidata is None:
        print("  Nao foi possivel encontrar solucao, mesmo com remanejamento.")
        return

    print(f"\n  Seria necessario remanejar:")
    print(f"  #{candidata.id} | {candidata.stakeholder['nome']} | {candidata.descricao()}")

    conf = input("  Deseja remanejar e agendar? (s/n): ").strip().lower()
    if conf != "s":
        print("  Cancelado.")
        return

    solver.remover_reuniao(candidata)
    sucesso = solver.agendar(reuniao)
    if sucesso:
        print(f"\n  Reuniao agendada: {reuniao.descricao()}")
        print(f"  Reuniao #{candidata.id} ({candidata.stakeholder['nome']}) foi removida e precisa ser reagendada.")
    else:
        print("  Falha ao agendar apos remanejamento.")


def listar_reunioes(solver):
    print("\n--- REUNIOES AGENDADAS ---")
    agendadas = [r for r in solver.reunioes if r.agendada]
    if not agendadas:
        print("  Nenhuma reuniao agendada.")
        return
    for r in sorted(agendadas, key=lambda x: (x.dia_agendado, x.slot_inicio)):
        print(f"  #{r.id:02d} | {r.descricao()}")


def remover_reuniao(solver):
    print("\n--- REMOVER REUNIAO ---")
    agendadas = [r for r in solver.reunioes if r.agendada]
    if not agendadas:
        print("  Nenhuma reuniao agendada.")
        return

    for r in agendadas:
        print(f"  [{r.id}] {r.stakeholder['nome']} — {r.descricao()}")

    ids_validos = [r.id for r in agendadas]
    while True:
        try:
            rid = int(input("  ID da reuniao a remover (0 = cancelar): "))
            if rid == 0:
                return
            if rid in ids_validos:
                break
            print(f"  Erro: ID invalido.")
        except ValueError:
            print("  Erro: Digite um numero.")

    reuniao = next(r for r in agendadas if r.id == rid)
    conf = input(f"  Remover reuniao #{rid}? (s/n): ").strip().lower()
    if conf == "s":
        solver.remover_reuniao(reuniao)
        print("  Reuniao removida.")
    else:
        print("  Cancelado.")


def main():
    solver = AgendaSolver()

    while True:
        print("\n========================================")
        print("  SISTEMA DE AGENDA")
        print("========================================")
        print("  [1] Nova reuniao")
        print("  [2] Ver agenda semanal")
        print("  [3] Listar reunioes")
        print("  [4] Remover reuniao")
        print("  [0] Sair")

        opcao = input("  Opcao: ").strip()

        if opcao == "1":
            nova_reuniao(solver)
        elif opcao == "2":
            solver.exibir_agenda()
        elif opcao == "3":
            listar_reunioes(solver)
        elif opcao == "4":
            remover_reuniao(solver)
        elif opcao == "0":
            print("  Ate logo!")
            sys.exit(0)
        else:
            print("  Opcao invalida.")


if __name__ == "__main__":
    main()
