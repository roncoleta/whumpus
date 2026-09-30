"""AGENTE A — Reativo simples (Aula 4, tipo 1).                      [0,3 ponto]

Regras condição → ação, SEM MEMÓRIA: a decisão depende apenas da percepção atual.
Não guarde nada em self entre chamadas (nada de casas visitadas, "já peguei o ouro"
etc.). É o baseline do experimento e existe para mostrar o limite dos reativos.

Perguntas para guiar o projeto das regras:
  - O que fazer quando há brilho? E quando há brisa ou fedor?
  - Sem memória, como o agente sabe que já está com o ouro? E como volta a (1,1)?
  - O que fazer depois de um baque?
  - Qual regra evita que ele fique girando para sempre?

No relatório, explique quais mundos derrotam este agente e por quê.
"""
"""AGENTE A — Reativo simples (Aula 4, tipo 1).                      [0,3 ponto]

Regras condição → ação, SEM MEMÓRIA: a decisão depende apenas da percepção atual.
Nada é guardado em self entre chamadas.

Como o agente sabe que já pegou o ouro, ou que está "chegando" em (1,1)?
  * Ele NÃO sabe se pegou o ouro. Por isso a regra de sair é: "se estou em (1,1)
    virado para OESTE ou SUL, SAIR". A partida começa virada para LESTE, então só se
    chega a (1,1) virado assim ao VOLTAR andando. Isso é memória embutida na
    percepção (direção), não no agente.
  * Em perigo (brisa/fedor) o agente recua na direção de (1,1). Se o recuo terminar em
    (1,1), ele sai. Com o ouro isso rende +1000; sem ele, só −1 ponto por ação.

Como não gira para sempre? Os giros aleatórios entre casas calmas quebram os ciclos.
O sorteio usa um gerador no nível do MÓDULO, com semente fixa (reprodutível), e não
guarda nada sobre o mundo: a decisão continua sendo função só da percepção atual.

Limites (para o relatório): sem memória, ele não evita voltar a casas já visitadas, não
sabe se tem o ouro e recua de qualquer sensação, então perde muitos mundos solúveis.
"""
import random

from wumpus import Acao, Agente, Direcao, INICIO, Percepcao

_RNG = random.Random(2024)   # ruído do módulo; NÃO é memória do agente


def _virar_para(atual: Direcao, alvo: Direcao) -> Acao:
    """Ação que aproxima `atual` de `alvo` (AVANCAR se já está virado para ele)."""
    if atual == alvo:
        return Acao.AVANCAR
    if alvo == atual.esquerda():
        return Acao.VIRAR_ESQUERDA
    return Acao.VIRAR_DIREITA


class AgenteReativo(Agente):
    nome = "A · Reativo"

    def agir(self, p: Percepcao) -> Acao:
        # R1: ouro aqui => pegar
        if p.brilho:
            return Acao.AGARRAR

        # Sem posição/direção não há como se orientar sem memória: só reage a sensores
        if p.posicao is None:
            if p.baque:
                return Acao.VIRAR_DIREITA
            if p.brisa or p.fedor:
                return _RNG.choice([Acao.VIRAR_DIREITA, Acao.VIRAR_ESQUERDA])
            return _RNG.choice([Acao.AVANCAR, Acao.AVANCAR, Acao.AVANCAR, Acao.VIRAR_DIREITA])

        x, y = p.posicao
        d = p.direcao

        # R2: cheguei em (1,1) andando (virado para OESTE/SUL) => sair
        if (x, y) == INICIO and d in (Direcao.OESTE, Direcao.SUL):
            return Acao.SAIR

        # R3: bati na parede => girar
        if p.baque:
            return Acao.VIRAR_DIREITA

        # R4: perigo (brisa ou fedor) => recuar em direção a (1,1)
        if p.brisa or p.fedor:
            rumo_casa = Direcao.OESTE if x > 1 else Direcao.SUL
            return _virar_para(d, rumo_casa)

        # R5: casa calma (todas as vizinhas são seguras) => explorar, com giros ao acaso
        return _RNG.choice([Acao.AVANCAR, Acao.AVANCAR, Acao.AVANCAR,
                            Acao.VIRAR_ESQUERDA, Acao.VIRAR_DIREITA])
