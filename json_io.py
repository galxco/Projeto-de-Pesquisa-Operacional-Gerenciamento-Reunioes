
import json
import os
from models import SALAS, STAKEHOLDERS, DIAS_SEMANA, SLOT_DURACAO_MIN, slot_para_hora, criar_sala
from models import Reuniao


# ─── EXPORTAR ────────────────────────────────────────────────────────────────

def exportar_json(solver, caminho: str = "agenda_export.json") -> bool:
    """
    Exporta salas cadastradas e todas as reuniões agendadas para JSON.
    """
    dados = {
        "salas": [
            {"id": s["id"], "nome": s["nome"], "capacidade": s["capacidade"]}
            for s in SALAS
        ],
        "reunioes": []
    }

    for r in solver.reunioes:
        entrada = {
            "id":               r.id,
            "stakeholder_id":   r.stakeholder["id"],
            "stakeholder_nome": r.stakeholder["nome"],
            "extras":           r.extras,
            "total_pessoas":    r.total_pessoas,
            "duracao_slots":    r.duracao_slots,
            "duracao_horas":    round(r.duracao_slots * SLOT_DURACAO_MIN / 60, 2),
            "dias_possiveis":   r.dias_possiveis,
            "agendada":         r.agendada,
        }
        if r.agendada:
            fim = r.slot_inicio + r.duracao_slots
            entrada.update({
                "dia_agendado":   r.dia_agendado,
                "dia_nome":       DIAS_SEMANA[r.dia_agendado],
                "slot_inicio":    r.slot_inicio,
                "horario_inicio": slot_para_hora(r.slot_inicio),
                "horario_fim":    slot_para_hora(fim),
                "sala_id":        r.sala["id"],
                "sala_nome":      r.sala["nome"],
            })
        dados["reunioes"].append(entrada)

    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"  Erro ao salvar arquivo: {e}")
        return False


# ─── IMPORTAR SALAS ──────────────────────────────────────────────────────────

def importar_salas(solver, caminho: str) -> tuple[int, list[str]]:
    """
    Lê um JSON com lista de salas e adiciona as que ainda não existem.
    """
    erros = []

    if not os.path.isfile(caminho):
        return 0, [f"Arquivo nao encontrado: {caminho}"]

    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except json.JSONDecodeError as e:
        return 0, [f"JSON invalido: {e}"]

    lista = dados.get("salas", [])
    if not isinstance(lista, list):
        return 0, ["Campo 'salas' deve ser uma lista."]

    adicionadas = 0
    for i, item in enumerate(lista):
        nome       = item.get("nome", "").strip()
        capacidade = item.get("capacidade")

        if not nome:
            erros.append(f"Item {i}: campo 'nome' ausente ou vazio.")
            continue
        if not isinstance(capacidade, int) or capacidade < 1:
            erros.append(f"Item {i} ('{nome}'): 'capacidade' deve ser inteiro >= 1.")
            continue
        if any(s["nome"].lower() == nome.lower() for s in SALAS):
            erros.append(f"Item {i}: sala '{nome}' ja existe — ignorada.")
            continue

        sala = criar_sala(nome, capacidade)
        SALAS.append(sala)
        solver.registrar_nova_sala(sala)
        adicionadas += 1

    return adicionadas, erros


# ─── IMPORTAR REUNIÕES ───────────────────────────────────────────────────────

def importar_reunioes(solver, caminho: str, proximo_id_fn) -> tuple[int, int, list[str]]:
    """
    Lê um JSON com lista de reuniões e tenta agendá-las.
    """
    erros = []

    if not os.path.isfile(caminho):
        return 0, 0, [f"Arquivo nao encontrado: {caminho}"]

    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except json.JSONDecodeError as e:
        return 0, 0, [f"JSON invalido: {e}"]

    lista = dados.get("reunioes", [])
    if not isinstance(lista, list):
        return 0, 0, ["Campo 'reunioes' deve ser uma lista."]

    ids_stakeholders = {s["id"] for s in STAKEHOLDERS}
    agendadas = falhas = 0

    for i, item in enumerate(lista):
        sid        = item.get("stakeholder_id")
        extras     = item.get("extras", 0)
        duracao    = item.get("duracao_slots")
        dias       = item.get("dias_possiveis", [])

        # Validações
        if sid not in ids_stakeholders:
            erros.append(f"Item {i}: stakeholder_id={sid} invalido.")
            falhas += 1
            continue
        if not isinstance(extras, int) or extras < 0:
            erros.append(f"Item {i}: 'extras' deve ser inteiro >= 0.")
            falhas += 1
            continue
        if not isinstance(duracao, int) or not (1 <= duracao <= 8):
            erros.append(f"Item {i}: 'duracao_slots' deve ser inteiro entre 1 e 8.")
            falhas += 1
            continue
        if not isinstance(dias, list) or not dias or not all(0 <= d <= 4 for d in dias):
            erros.append(f"Item {i}: 'dias_possiveis' deve ser lista com valores entre 0 e 4.")
            falhas += 1
            continue

        stakeholder = next(s for s in STAKEHOLDERS if s["id"] == sid)
        reuniao = Reuniao(
            id=proximo_id_fn(),
            stakeholder=stakeholder,
            extras=extras,
            duracao_slots=duracao,
            dias_possiveis=sorted(set(dias)),
        )

        if solver.agendar(reuniao):
            agendadas += 1
        else:
            erros.append(f"Item {i} (stakeholder '{stakeholder['nome']}'): sem horario disponivel.")
            falhas += 1

    return agendadas, falhas, erros


# ─── MENU JSON ───────────────────────────────────────────────────────────────

def menu_json(solver, proximo_id_fn):
    while True:
        print("\n--- IMPORTAR / EXPORTAR JSON ---")
        print("  [1] Exportar agenda completa")
        print("  [2] Importar salas de arquivo JSON")
        print("  [3] Importar reunioes de arquivo JSON")
        print("  [0] Voltar")

        opcao = input("  Opcao: ").strip()

        # ── Exportar ──────────────────────────────────────────────────────────
        if opcao == "1":
            caminho = input("  Nome do arquivo [agenda_export.json]: ").strip()
            if not caminho:
                caminho = "agenda_export.json"
            if not caminho.endswith(".json"):
                caminho += ".json"

            ok = exportar_json(solver, caminho)
            if ok:
                print(f"  Exportado com sucesso: {os.path.abspath(caminho)}")
                print(f"  Total de salas   : {len(SALAS)}")
                print(f"  Total de reunioes: {len(solver.reunioes)}")

        # ── Importar salas ────────────────────────────────────────────────────
        elif opcao == "2":
            caminho = input("  Caminho do arquivo JSON de salas: ").strip()
            if not caminho:
                print("  Cancelado.")
                continue

            adicionadas, erros = importar_salas(solver, caminho)
            print(f"\n  Salas adicionadas: {adicionadas}")
            if erros:
                print("  Avisos/Erros:")
                for e in erros:
                    print(f"    - {e}")

        # ── Importar reunioes ─────────────────────────────────────────────────
        elif opcao == "3":
            if not SALAS:
                print("  Erro: Nenhuma sala cadastrada. Importe ou adicione salas primeiro.")
                continue

            caminho = input("  Caminho do arquivo JSON de reunioes: ").strip()
            if not caminho:
                print("  Cancelado.")
                continue

            ag, fa, erros = importar_reunioes(solver, caminho, proximo_id_fn)
            print(f"\n  Reunioes agendadas: {ag}")
            print(f"  Falhas            : {fa}")
            if erros:
                print("  Avisos/Erros:")
                for e in erros:
                    print(f"    - {e}")

        elif opcao == "0":
            break
        else:
            print("  Opcao invalida.")
