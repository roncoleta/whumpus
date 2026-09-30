"""AGENTE C — Lógico + objetivo, com planejamento por BFS (Aulas 3, 4 e 6).  [0,6 ponto]

Reaproveita o Agente B para saber ONDE é seguro e usa busca em largura (BFS)
para planejar COMO chegar lá. Máquina de estados sugerida (slide 10):

  EXPLORAR  → BFS até a casa segura não visitada mais próxima
  AGARRAR   → quando houver brilho na casa atual
  VOLTAR    → BFS até (1,1) passando apenas por casas provadas seguras
  SAIR      → chegou em (1,1) com o ouro

Decisão aberta — o dilema do risco: sem casa segura e sem ouro, o agente deve
sair, atirar a flecha (−10) ou arriscar uma casa incerta? Decidam por utilidade
esperada e justifiquem no relatório.

A função acoes_para_vizinho() (em wumpus) transforma cada passo do caminho da BFS
em giros + AVANCAR. A BFS em si é implementação do grupo.
"""

from wumpus import Acao, Direcao, INICIO, Percepcao
from agentes.agente_logico import AgenteLogico, _sim


def _sinal(n):
    return (n > 0) - (n < 0)


class AgenteObjetivo(AgenteLogico):
    nome = "C · Lógico + BFS"

    def __init__(self):
        super().__init__()
        self.fase = "explorar"
        self.plano = []   

    #auxiliares
    def _giros(self, atual: Direcao, alvo: Direcao):
        if alvo == atual:
            return []
        if alvo == atual.direita():
            return [Acao.VIRAR_DIREITA]
        if alvo == atual.esquerda():
            return [Acao.VIRAR_ESQUERDA]
        return [Acao.VIRAR_DIREITA, Acao.VIRAR_DIREITA]

    def _planejar_ate(self, destinos):
        caminho = self.bfs(self.posicao, destinos, self.casas_seguras)
        if caminho is None:
            return None
        acoes, _ = self._acoes_do_caminho(caminho)
        return acoes

    def _localizar_wumpus(self):
        candidatas = [(x, y)
                      for x in range(1, self.tamanho + 1)
                      for y in range(1, self.tamanho + 1)
                      if (x, y) != INICIO and not self.bc.ask((_sim("W", (x, y)), False))]
        return candidatas[0] if len(candidatas) == 1 else None

    def _planejar_tiro(self):
        if not (self.tem_flecha and self.wumpus_vivo):
            return None
        alvo = self._localizar_wumpus()
        if alvo is None:
            return None
        melhor = None
        for s in self.casas_seguras:
            if s == alvo or not (s[0] == alvo[0] or s[1] == alvo[1]):
                continue
            caminho = self.bfs(self.posicao, {s}, self.casas_seguras)
            if caminho is None:
                continue
            acoes, dir_final = self._acoes_do_caminho(caminho)
            dir_tiro = Direcao.de_delta((_sinal(alvo[0] - s[0]), _sinal(alvo[1] - s[1])))
            plano = acoes + self._giros(dir_final, dir_tiro) + [Acao.ATIRAR]
            if melhor is None or len(plano) < len(melhor):
                melhor = plano
        return melhor

    #decisão
    def agir(self, percepcao: Percepcao) -> Acao:
        self._atualizar_conhecimento(percepcao)     

        # AGARRAR tem prioridade sobre qualquer plano
        if percepcao.brilho and not self.tem_ouro:
            self.tem_ouro = True
            self.fase = "voltar"
            self.plano = []
            return self._emitir(Acao.AGARRAR)

        # Executa o plano em andamento 
        if self.plano:
            return self._emitir(self.plano.pop(0))

        # VOLTAR / SAIR
        if self.tem_ouro or self.fase == "voltar":
            if self.posicao == INICIO:
                return self._emitir(Acao.SAIR)
            self.fase = "voltar"
            plano = self._planejar_ate({INICIO})
            if plano:
                self.plano = plano
                return self._emitir(self.plano.pop(0))
            return self._emitir(Acao.SAIR)

        # EXPLORAR
        destinos = self.casas_seguras - self.casas_visitadas
        if destinos:
            self.fase = "explorar"
            plano = self._planejar_ate(destinos)
            if plano:
                self.plano = plano
                return self._emitir(self.plano.pop(0))

        # Sem casa segura e sem ouro, no caso é um risco
        plano = self._planejar_tiro()
        if plano:
            self.fase = "atirar"
            self.plano = plano
            return self._emitir(self.plano.pop(0))

        self.fase = "voltar"
        if self.posicao == INICIO:
            return self._emitir(Acao.SAIR)
        plano = self._planejar_ate({INICIO})
        if plano:
            self.plano = plano
            return self._emitir(self.plano.pop(0))
        return self._emitir(Acao.SAIR)

    def depurar(self) -> str:
        return (f"Fase: {self.fase} | Plano: {[str(a) for a in self.plano]} | "
                + super().depurar())