"""Testes da BC / resolução (Agente B) e checagens dos três agentes.

Rodar:  python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentes.agente_logico import (AgenteLogico, BaseConhecimento, eh_tautologia,
                                   para_cnf, pl_resolucao, resolver)
from agentes.agente_objetivo import AgenteObjetivo
from agentes.agente_reativo import AgenteReativo
from wumpus import Acao, MundoWumpus


def cnf(sentenca):
    return {frozenset(c) for c in para_cnf(sentenca)}


class TestCNF(unittest.TestCase):
    def test_bicondicional(self):
        esperado = {
            frozenset({("B", False), ("P1", True), ("P2", True)}),
            frozenset({("B", True), ("P1", False)}),
            frozenset({("B", True), ("P2", False)}),
        }
        self.assertEqual(cnf(("bicond", "B", ("ou", "P1", "P2"))), esperado)

    def test_implicacao_e_de_morgan(self):
        # ¬(A ∧ B) ≡ ¬A ∨ ¬B
        self.assertEqual(cnf(("nao", ("e", "A", "B"))),
                         {frozenset({("A", False), ("B", False)})})
        # A ⇒ B ≡ ¬A ∨ B
        self.assertEqual(cnf(("implica", "A", "B")),
                         {frozenset({("A", False), ("B", True)})})

    def test_distribuicao(self):
        # A ∨ (B ∧ C) ≡ (A ∨ B) ∧ (A ∨ C)
        self.assertEqual(cnf(("ou", "A", ("e", "B", "C"))),
                         {frozenset({("A", True), ("B", True)}),
                          frozenset({("A", True), ("C", True)})})


class TestResolucao(unittest.TestCase):
    def test_resolver(self):
        c1 = frozenset({("A", True), ("B", True)})
        c2 = frozenset({("A", False), ("C", True)})
        self.assertEqual(resolver(c1, c2), {frozenset({("B", True), ("C", True)})})

    def test_resolvente_tautologico_descartado(self):
        c1 = frozenset({("A", True), ("B", True)})
        c2 = frozenset({("A", False), ("B", False)})
        self.assertEqual(resolver(c1, c2), set())

    def test_clausula_vazia(self):
        self.assertTrue(pl_resolucao([frozenset({("A", True)})], ("A", True)))

    def test_modus_ponens(self):
        bc = BaseConhecimento()
        bc.tell(("implica", "A", "B"))
        bc.tell("A")
        self.assertTrue(bc.ask(("B", True)))
        self.assertFalse(bc.ask(("B", False)))

    def test_nao_deriva_o_que_nao_segue(self):
        bc = BaseConhecimento()
        bc.tell(("ou", "A", "B"))
        self.assertFalse(bc.ask(("A", True)))
        self.assertFalse(bc.ask(("B", True)))
        self.assertTrue(bc.ask(("A", False)) is False)

    def test_brisa_ausente_prova_vizinhos_sem_poco(self):
        bc = BaseConhecimento()
        bc.tell(("bicond", "B11", ("ou", "P12", "P21")))
        bc.tell(("nao", "B11"))
        self.assertTrue(bc.ask(("P12", False)))
        self.assertTrue(bc.ask(("P21", False)))
        self.assertFalse(bc.ask(("P22", False)))

    def test_um_unico_wumpus(self):
        bc = BaseConhecimento()
        bc.tell(("ou", "W12", "W21"))
        bc.tell(("ou", ("nao", "W12"), ("nao", "W21")))
        bc.tell(("nao", "W12"))
        self.assertTrue(bc.ask(("W21", True)))


class TestAgentes(unittest.TestCase):
    def jogar(self, agente, mundo):
        p = mundo.percepcao()
        while not mundo.terminado:
            p = mundo.executar(agente.agir(p))
        return mundo

    def test_b_nunca_morre_nas_sementes_publicas(self):
        for s in range(60):
            m = self.jogar(AgenteLogico(), MundoWumpus.gerar(s))
            self.assertFalse(m.morreu, f"B morreu na semente {s}")

    def test_c_nunca_morre_nas_sementes_publicas(self):
        for s in range(60):
            m = self.jogar(AgenteObjetivo(), MundoWumpus.gerar(s))
            self.assertFalse(m.morreu, f"C morreu na semente {s}")

    def test_b_e_c_no_mundo_classico(self):
        for cls in (AgenteLogico, AgenteObjetivo):
            m = self.jogar(cls(), MundoWumpus.classico())
            self.assertFalse(m.morreu)

    def test_c_pega_ouro_quando_ha_caminho_provado(self):
        # Mundo sem perigo perto do ouro: B e C têm de sair com ele
        for cls in (AgenteLogico, AgenteObjetivo):
            m = MundoWumpus(wumpus=(4, 4), ouro=(2, 2), pocos=[(4, 1)])
            self.jogar(cls(), m)
            self.assertTrue(m.sucesso, cls.__name__)

    def test_a_nao_guarda_estado(self):
        a = AgenteReativo()
        antes = dict(vars(a))
        m = MundoWumpus.gerar(3)
        p = m.percepcao()
        for _ in range(20):
            if m.terminado:
                break
            p = m.executar(a.agir(p))
        self.assertEqual(vars(a), antes, "Agente A guardou algo em self")

    def test_a_devolve_sempre_uma_acao(self):
        for s in range(30):
            m = MundoWumpus.gerar(s)
            a = AgenteReativo()
            p = m.percepcao()
            while not m.terminado:
                acao = a.agir(p)
                self.assertIsInstance(acao, Acao)
                p = m.executar(acao)


if __name__ == "__main__":
    unittest.main()