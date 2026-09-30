"""AGENTE B — Agente lógico baseado em conhecimento (Aula 6).        [1,3 ponto]

Ciclo: PERCEPÇÃO → TELL → BC → ASK (resolução) → AÇÃO

Critérios de avaliação (slide 08):
  1. Axiomas gerados por código para as casas (nada escrito à mão casa a casa):
        ¬P(1,1)   ¬W(1,1)
        B(x,y) ⇔ P(vizinhos)   em disjunção
        F(x,y) ⇔ W(vizinhos)   em disjunção
  2. Percepções entram na BC SOMENTE via tell().
  3. A segurança de uma casa é decidida SOMENTE via ask(), por resolução por
     refutação: BC ∧ ¬α ⊢ □ (cláusula vazia)  ⇒  BC ⊨ α.
  4. Nada de "if brisa: evitar vizinhos" escondido no código.

Regras do jogo (slide 13):
  - A conversão para CNF e a resolução são implementadas pelo grupo.
  - sympy, pysat e z3 NÃO podem ser usados aqui; só em testes, para conferir resultados.

Dica de engenharia (slide 09): instancie as regras B e F apenas para as casas já
visitadas e guarde em cache as respostas de ask(). A BC enxuta é o que torna a
resolução tratável.

Liberdade de projeto: a representação de sentenças, literais e cláusulas é do grupo.
Uma sugestão simples é literal = (simbolo, positivo), por exemplo ("P13", False)
para ¬P(1,3), e cláusula = frozenset de literais. Justifique a escolha no relatório.
"""

from collections import deque
from itertools import product

from wumpus import Acao, Agente, Direcao, Percepcao, INICIO, acoes_para_vizinho, vizinhos

# 1) Conversão para CNF
def _sem_implicacoes(s):
    if isinstance(s, str):
        return s
    op, *args = s
    args = [_sem_implicacoes(a) for a in args]
    if op == "implica":
        a, b = args
        return ("ou", ("nao", a), b)
    if op == "bicond":
        a, b = args
        return ("e", ("ou", ("nao", a), b), ("ou", ("nao", b), a))
    return (op, *args)


def _nnf(s, negado=False):
    if isinstance(s, str):
        return ("lit", s, not negado)
    op, *args = s
    if op == "nao":
        return _nnf(args[0], not negado)
    if op in ("e", "ou"):
        novo_op = op if not negado else ("ou" if op == "e" else "e")
        return (novo_op, *[_nnf(a, negado) for a in args])
    raise ValueError(f"operador desconhecido: {op}")


def _distribuir(s):
    op = s[0]
    if op == "lit":
        return {frozenset({(s[1], s[2])})}
    filhos = [_distribuir(a) for a in s[1:]]
    if op == "e":
        return set().union(*filhos)
    # op == "ou": produto cartesiano das cláusulas de cada filho
    resultado = set()
    for combinacao in product(*filhos):
        resultado.add(frozenset().union(*combinacao))
    return resultado


def para_cnf(sentenca):
    return [c for c in _distribuir(_nnf(_sem_implicacoes(sentenca))) if not eh_tautologia(c)]

# 2) Resolução
def negar(literal):
    simbolo, positivo = literal
    return (simbolo, not positivo)


def eh_tautologia(clausula) -> bool:
    return any(negar(l) in clausula for l in clausula)


def resolver(c1, c2):
    resolventes = set()
    for lit in c1:
        comp = negar(lit)
        if comp in c2:
            novo = (c1 - {lit}) | (c2 - {comp})
            if not eh_tautologia(novo):
                resolventes.add(frozenset(novo))
    return resolventes


def pl_resolucao(clausulas, consulta) -> bool:
    negacao = frozenset({negar(consulta)})
    todas = set(clausulas)
    todas.add(negacao)
    apoio = {negacao}  

    while apoio:
        novas = set()
        for c in apoio:
            for d in todas:
                for r in resolver(c, d):
                    if not r:  
                        return True
                    if r in todas or r in novas:
                        continue
                    if any(k <= r for k in todas): 
                        continue
                    novas.add(r)
        todas |= novas
        apoio = novas
    return False

# 3) Base de conhecimento
class BaseConhecimento:

    def __init__(self):
        self.clausulas = set()
        self._cache = {}

    def tell(self, sentenca) -> None:
        modificou = False
        for c in para_cnf(sentenca):
            if c not in self.clausulas:
                self.clausulas.add(c)
                modificou = True
        if modificou:
            self._cache.clear()

    def ask(self, consulta) -> bool:
        if consulta not in self._cache:
            self._cache[consulta] = pl_resolucao(self.clausulas, consulta)
        return self._cache[consulta]


# 4) Agente B
def _sim(prefixo, pos):
    return f"{prefixo}{pos[0]}{pos[1]}"


def _fato(simbolo, valor):
    return simbolo if valor else ("nao", simbolo)


class AgenteLogico(Agente):
    nome = "B · Lógico"

    def __init__(self):
        super().__init__()
        self.bc = BaseConhecimento()
        self.tamanho = 4

        self.posicao = INICIO
        self.direcao = Direcao.LESTE
        self._pos_antes = INICIO
        self._ultima = None

        self.tem_ouro = False
        self.tem_flecha = True
        self.wumpus_vivo = True

        self.casas_visitadas = set()
        self.casas_seguras = set()
        self._axiomas_prontos = set()

        # Conhecimento inicial: a casa de partida é segura
        self.bc.tell(_fato(_sim("P", INICIO), False))
        self.bc.tell(_fato(_sim("W", INICIO), False))
        self._axiomas_um_wumpus()

    def _axiomas_um_wumpus(self):
        casas = [(x, y) for x in range(1, self.tamanho + 1)
                 for y in range(1, self.tamanho + 1) if (x, y) != INICIO]
        self.bc.tell(("ou", *[_sim("W", c) for c in casas]))
        for i, a in enumerate(casas):
            for b in casas[i + 1:]:
                self.bc.tell(("ou", ("nao", _sim("W", a)), ("nao", _sim("W", b))))

    #axiomas
    def _instanciar_axiomas_casa(self, pos):
        """B(x,y) ⇔ P(viz1) ∨ P(viz2) ...   e   F(x,y) ⇔ W(viz1) ∨ W(viz2) ..."""
        if pos in self._axiomas_prontos:
            return
        self._axiomas_prontos.add(pos)
        viz = vizinhos(pos, self.tamanho)
        self.bc.tell(("bicond", _sim("B", pos), ("ou", *[_sim("P", v) for v in viz])))
        self.bc.tell(("bicond", _sim("F", pos), ("ou", *[_sim("W", v) for v in viz])))

    #TELL + ASK
    def _sincronizar(self, p: Percepcao):
        """Mantém posição/direção: usa a percepção se existir, senão estima pelas ações."""
        if p.posicao is not None:
            self.posicao, self.direcao = p.posicao, p.direcao
        elif p.baque and self._ultima is Acao.AVANCAR:
            self.posicao = self._pos_antes   

    def _atualizar_conhecimento(self, p: Percepcao):
        self._sincronizar(p)
        pos = self.posicao
        self.casas_visitadas.add(pos)
        self.casas_seguras.add(pos)

        if p.grito:
            self.wumpus_vivo = False

        #TELL
        self._instanciar_axiomas_casa(pos)
        self.bc.tell(_fato(_sim("B", pos), p.brisa))
        if self.wumpus_vivo:              
            self.bc.tell(_fato(_sim("F", pos), p.fedor))
        self.bc.tell(_fato(_sim("P", pos), False)) 
        if self.wumpus_vivo:
            self.bc.tell(_fato(_sim("W", pos), False))

        self._inferir_seguras()

    def _inferir_seguras(self):
        fronteira = {v for c in self.casas_visitadas for v in vizinhos(c, self.tamanho)}
        fronteira -= self.casas_seguras
        for pos in sorted(fronteira):
            if not self.bc.ask((_sim("P", pos), False)):
                continue
            if self.wumpus_vivo and not self.bc.ask((_sim("W", pos), False)):
                continue
            self.casas_seguras.add(pos)
            self.bc.tell(_fato(_sim("P", pos), False))
            if self.wumpus_vivo:
                self.bc.tell(_fato(_sim("W", pos), False))

    #navegação
    def bfs(self, origem, destinos, permitidas):
        if origem in destinos:
            return [origem]
        fila = deque([[origem]])
        visitados = {origem}
        while fila:
            caminho = fila.popleft()
            atual = caminho[-1]
            if atual in destinos:
                return caminho
            for viz in vizinhos(atual, self.tamanho):
                if viz in permitidas and viz not in visitados:
                    visitados.add(viz)
                    fila.append(caminho + [viz])
        return None

    def _acoes_do_caminho(self, caminho):
        acoes, d = [], self.direcao
        for a, b in zip(caminho, caminho[1:]):
            acoes += acoes_para_vizinho(a, d, b)
            d = Direcao.de_delta((b[0] - a[0], b[1] - a[1]))
        return acoes, d

    def _emitir(self, acao: Acao) -> Acao:
        self._ultima = acao
        self._pos_antes = self.posicao
        if acao is Acao.VIRAR_ESQUERDA:
            self.direcao = self.direcao.esquerda()
        elif acao is Acao.VIRAR_DIREITA:
            self.direcao = self.direcao.direita()
        elif acao is Acao.AVANCAR:
            dx, dy = self.direcao.delta
            self.posicao = (self.posicao[0] + dx, self.posicao[1] + dy)
        elif acao is Acao.ATIRAR:
            self.tem_flecha = False
        return acao

    def _ir_para(self, destinos):
        caminho = self.bfs(self.posicao, destinos, self.casas_seguras)
        if not caminho:
            return None
        acoes, _ = self._acoes_do_caminho(caminho)
        return self._emitir(acoes[0]) if acoes else None

    #decisão
    def agir(self, percepcao: Percepcao) -> Acao:
        self._atualizar_conhecimento(percepcao)

        if percepcao.brilho and not self.tem_ouro:
            self.tem_ouro = True
            return self._emitir(Acao.AGARRAR)

        if self.tem_ouro:
            if self.posicao == INICIO:
                return self._emitir(Acao.SAIR)
            acao = self._ir_para({INICIO})
            if acao:
                return acao

        else:
            novas = self.casas_seguras - self.casas_visitadas
            if novas:
                acao = self._ir_para(novas)
                if acao:
                    return acao

        if self.posicao != INICIO:
            acao = self._ir_para({INICIO})
            if acao:
                return acao
        return self._emitir(Acao.SAIR)

    def depurar(self) -> str:
        seguras = sorted(self.casas_seguras - self.casas_visitadas)
        return (f"BC: {len(self.bc.clausulas)} cláusulas | "
                f"seguras a explorar: {seguras} | ouro: {self.tem_ouro}")