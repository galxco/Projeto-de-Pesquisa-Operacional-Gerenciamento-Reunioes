DIAS_SEMANA = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
}

# Cada slot = 30 minutos | slot 0 = 08:00 | slot 18 = 17:30
SLOT_DURACAO_MIN = 30
SLOTS_POR_DIA    = 19       # slots 0 a 18
SLOTS_ALMOCO     = {8, 9, 10}  # 12:00, 12:30, 13:00 — bloqueados

def slot_para_hora(slot):
    minutos = 8 * 60 + slot * SLOT_DURACAO_MIN
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


# Salas disponíveis: lista de dicionários simples
SALAS = [
    {"id": 0, "nome": "Sala Pequena", "capacidade": 6},
    {"id": 1, "nome": "Sala Media",   "capacidade": 15},
    {"id": 2, "nome": "Sala Grande",  "capacidade": 20},
]

# Stakeholders: lista de dicionários simples
STAKEHOLDERS = [
    {"id": 0, "nome": "TechNova",   "num_pessoas": 4,  "prioridade": 2},
    {"id": 1, "nome": "IAnovidade", "num_pessoas": 6,  "prioridade": 5},
    {"id": 2, "nome": "MobileInc.", "num_pessoas": 5,  "prioridade": 1},
    {"id": 3, "nome": "ComexCia",   "num_pessoas": 15, "prioridade": 4},
]


class Reuniao:
    """Representa uma reunião a ser agendada."""

    def __init__(self, id, stakeholder, extras, duracao_slots, dias_possiveis):
        self.id               = id
        self.stakeholder      = stakeholder        # dicionário de STAKEHOLDERS
        self.extras           = extras             # pessoas além do grupo
        self.duracao_slots    = duracao_slots
        self.dias_possiveis   = dias_possiveis     # lista de índices 0-4

        # Preenchido após agendamento
        self.dia_agendado  = None
        self.slot_inicio   = None
        self.sala          = None                  # dicionário de SALAS

    @property
    def total_pessoas(self):
        return self.stakeholder["num_pessoas"] + self.extras

    @property
    def agendada(self):
        return self.dia_agendado is not None

    def descricao(self):
        if not self.agendada:
            return "Nao agendada"
        ini = slot_para_hora(self.slot_inicio)
        fim = slot_para_hora(self.slot_inicio + self.duracao_slots)
        dia = DIAS_SEMANA[self.dia_agendado]
        return f"{dia} | {ini} - {fim} | {self.sala['nome']} | {self.total_pessoas} pessoas"
