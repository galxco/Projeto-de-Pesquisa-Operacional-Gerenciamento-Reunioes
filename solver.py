from ortools.sat.python import cp_model
from models import DIAS_SEMANA, SLOTS_POR_DIA, SLOTS_ALMOCO, slot_para_hora


def salas_validas(salas, total_pessoas):
    """Retorna salas (da lista dinâmica) que comportam o grupo."""
    return [s for s in sorted(salas, key=lambda s: s["capacidade"])
            if s["capacidade"] >= total_pessoas]


def slots_validos(duracao):
    """Retorna slots de início válidos (sem sobrepor almoço)."""
    validos = []
    for s in range(SLOTS_POR_DIA - duracao + 1):
        if not set(range(s, s + duracao)).intersection(SLOTS_ALMOCO):
            validos.append(s)
    return validos


class AgendaSolver:

    def __init__(self, salas: list):
        self._salas  = salas         
        self.agenda  = {}
        self._rebuild_agenda()
        self.reunioes = []

    # ------------------------------------------------------------------
    # Gerência de agenda ao vivo
    # ------------------------------------------------------------------

    def _rebuild_agenda(self):
        """Reconstrói o dicionário de agenda com as salas atuais."""
        nova = {}
        for dia in range(5):
            nova[dia] = {}
            for s in self._salas:
                nova[dia][s["id"]] = self.agenda.get(dia, {}).get(s["id"], [])
        self.agenda = nova

    def registrar_nova_sala(self, sala: dict):
        """Adiciona entradas de agenda para uma sala recém-criada."""
        for dia in range(5):
            self.agenda[dia][sala["id"]] = []

    # ------------------------------------------------------------------
    # CP-SAT
    # ------------------------------------------------------------------

    def _resolver(self, reuniao, reunioes_fixas):
        """
        Usa CP-SAT para encontrar (dia, slot, sala).
        Retorna a tupla ou None se inviável.
        """
        model = cp_model.CpModel()

        dias  = reuniao.dias_possiveis
        slots = slots_validos(reuniao.duracao_slots)
        salas = salas_validas(self._salas, reuniao.total_pessoas)

        if not dias or not slots or not salas:
            return None

        # Variáveis
        dia_var  = model.NewIntVar(0, len(dias)  - 1, "dia")
        slot_var = model.NewIntVar(0, len(slots) - 1, "slot")
        sala_var = model.NewIntVar(0, len(salas) - 1, "sala")

        # Restrições de conflito
        for fixa in reunioes_fixas:
            if not fixa.agendada or fixa.dia_agendado not in dias:
                continue

            dia_idx  = dias.index(fixa.dia_agendado)
            ini_fixa = fixa.slot_inicio
            fim_fixa = fixa.slot_inicio + fixa.duracao_slots

            # Conflito de sala
            for si, sala in enumerate(salas):
                if fixa.sala["id"] != sala["id"]:
                    continue
                for sj, sp in enumerate(slots):
                    if sp < fim_fixa and sp + reuniao.duracao_slots > ini_fixa:
                        mesmo_dia  = model.NewBoolVar(f"d_{fixa.id}_{si}_{sj}")
                        mesmo_slot = model.NewBoolVar(f"s_{fixa.id}_{si}_{sj}")
                        mesma_sala = model.NewBoolVar(f"r_{fixa.id}_{si}_{sj}")
                        model.Add(dia_var  == dia_idx).OnlyEnforceIf(mesmo_dia)
                        model.Add(dia_var  != dia_idx).OnlyEnforceIf(mesmo_dia.Not())
                        model.Add(slot_var == sj).OnlyEnforceIf(mesmo_slot)
                        model.Add(slot_var != sj).OnlyEnforceIf(mesmo_slot.Not())
                        model.Add(sala_var == si).OnlyEnforceIf(mesma_sala)
                        model.Add(sala_var != si).OnlyEnforceIf(mesma_sala.Not())
                        model.AddBoolOr([mesmo_dia.Not(), mesmo_slot.Not(), mesma_sala.Not()])

            # Conflito de stakeholder
            if fixa.stakeholder["id"] == reuniao.stakeholder["id"]:
                for sj, sp in enumerate(slots):
                    if sp < fim_fixa and sp + reuniao.duracao_slots > ini_fixa:
                        mesmo_dia  = model.NewBoolVar(f"sd_{fixa.id}_{sj}")
                        mesmo_slot = model.NewBoolVar(f"ss_{fixa.id}_{sj}")
                        model.Add(dia_var  == dia_idx).OnlyEnforceIf(mesmo_dia)
                        model.Add(dia_var  != dia_idx).OnlyEnforceIf(mesmo_dia.Not())
                        model.Add(slot_var == sj).OnlyEnforceIf(mesmo_slot)
                        model.Add(slot_var != sj).OnlyEnforceIf(mesmo_slot.Not())
                        model.AddBoolOr([mesmo_dia.Not(), mesmo_slot.Not()])

        # Objetivo: sala menor primeiro, depois slot mais cedo
        model.Minimize(sala_var * len(slots) + slot_var)

        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return (
                dias[solver.Value(dia_var)],
                slots[solver.Value(slot_var)],
                salas[solver.Value(sala_var)],
            )
        return None

    # ------------------------------------------------------------------
    # Agendar
    # ------------------------------------------------------------------

    def agendar(self, reuniao):
        resultado = self._resolver(reuniao, self.reunioes)
        if resultado is None:
            return False

        dia, slot, sala = resultado
        reuniao.dia_agendado = dia
        reuniao.slot_inicio  = slot
        reuniao.sala         = sala
        self.agenda[dia][sala["id"]].append((slot, slot + reuniao.duracao_slots))
        self.reunioes.append(reuniao)
        return True

    # ------------------------------------------------------------------
    # Sugestão de remanejamento
    # ------------------------------------------------------------------

    def sugerir_remanejamento(self, reuniao):
        for candidata in self.reunioes:
            if not candidata.agendada:
                continue
            if candidata.stakeholder["prioridade"] >= reuniao.stakeholder["prioridade"]:
                continue
            fixas_sem = [r for r in self.reunioes if r is not candidata]
            if self._resolver(reuniao, fixas_sem) is not None:
                return candidata
        return None

    # ------------------------------------------------------------------
    # Remover
    # ------------------------------------------------------------------

    def remover_reuniao(self, reuniao):
        if reuniao.agendada:
            dia, sid = reuniao.dia_agendado, reuniao.sala["id"]
            self.agenda[dia][sid] = [
                (ini, fim) for ini, fim in self.agenda[dia][sid]
                if not (ini == reuniao.slot_inicio
                        and fim == reuniao.slot_inicio + reuniao.duracao_slots)
            ]
        reuniao.dia_agendado = None
        reuniao.slot_inicio  = None
        reuniao.sala         = None
        if reuniao in self.reunioes:
            self.reunioes.remove(reuniao)

    # ------------------------------------------------------------------
    # Visualização
    # ------------------------------------------------------------------

    def exibir_agenda(self):
        print("\n" + "=" * 60)
        print("  AGENDA SEMANAL")
        print("=" * 60)

        tem_algo = False
        for dia in range(5):
            eventos = []
            for sala in self._salas:
                sid = sala["id"]
                if sid not in self.agenda[dia]:
                    continue
                for ini, fim in self.agenda[dia][sid]:
                    r = next(
                        (r for r in self.reunioes
                         if r.agendada and r.dia_agendado == dia
                         and r.slot_inicio == ini and r.sala["id"] == sid),
                        None
                    )
                    if r:
                        eventos.append((ini, r, sala))

            if not eventos:
                continue

            tem_algo = True
            print(f"\n  {DIAS_SEMANA[dia]}")
            print("  " + "-" * 50)
            for ini, r, sala in sorted(eventos):
                fim = ini + r.duracao_slots
                print(
                    f"  {slot_para_hora(ini)} -> {slot_para_hora(fim)}"
                    f"  | {sala['nome']:<15}"
                    f"  | {r.stakeholder['nome']:<12}"
                    f"  | {r.total_pessoas} pessoas"
                )

        if not tem_algo:
            print("\n  Nenhuma reuniao agendada ainda.")
        print("=" * 60 + "\n")
