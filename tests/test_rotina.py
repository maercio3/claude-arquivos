import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rotina_compras import historico, relatorio
from rotina_compras.config import ItemWatchlist, Watchlist, WatchlistInvalida, carregar
from rotina_compras.fontes.base import FonteIndisponivel
from rotina_compras.modelo import Oferta, ResumoItem
from rotina_compras.rotina import coletar_item, executar

WATCHLIST_YAML = """
padroes:
  fontes: [mercado_livre, shopee]
  max_resultados: 4
itens:
  - nome: Fone TWS
    termos: fone bluetooth tws
    preco_alvo: 150
  - nome: Camiseta
    fontes: [shein]
"""


def oferta(item="Fone TWS", fonte="shopee", preco=100.0):
    return Oferta(item=item, fonte=fonte, titulo=f"{item} barato", preco=preco,
                  url="https://exemplo.com/x")


class TestWatchlist(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self.pasta.name) / "watchlist.yml"
        self.caminho.write_text(WATCHLIST_YAML, encoding="utf-8")
        self.addCleanup(self.pasta.cleanup)

    def test_le_itens_e_padroes(self):
        watchlist = carregar(self.caminho)
        self.assertEqual(len(watchlist), 2)
        primeiro = watchlist.itens[0]
        self.assertEqual(primeiro.preco_alvo, 150.0)
        self.assertEqual(primeiro.fontes, ("mercado_livre", "shopee"))
        self.assertEqual(primeiro.max_resultados, 4)

    def test_termos_caem_para_o_nome(self):
        watchlist = carregar(self.caminho)
        self.assertEqual(watchlist.itens[1].termos, "Camiseta")

    def test_fontes_do_item_vencem_o_padrao(self):
        watchlist = carregar(self.caminho)
        self.assertEqual(watchlist.itens[1].fontes, ("shein",))

    def test_arquivo_ausente(self):
        with self.assertRaises(WatchlistInvalida):
            carregar(Path(self.pasta.name) / "nao-existe.yml")

    def test_sem_itens(self):
        vazia = Path(self.pasta.name) / "vazia.yml"
        vazia.write_text("itens: []", encoding="utf-8")
        with self.assertRaises(WatchlistInvalida):
            carregar(vazia)


class TestColeta(unittest.TestCase):
    def test_fonte_indisponivel_nao_derruba_as_outras(self):
        item = ItemWatchlist(nome="Fone TWS", termos="fone", fontes=("mercado_livre", "shopee"))

        def falso_obter(nome):
            if nome == "mercado_livre":
                def quebrado(termo, limite):
                    raise FonteIndisponivel("token ausente")
                return quebrado
            return lambda termo, limite: [oferta()]

        with mock.patch("rotina_compras.rotina.obter", side_effect=falso_obter):
            resumo = coletar_item(item, pausa=0)

        self.assertEqual(len(resumo.ofertas), 1)
        self.assertIn("mercado_livre", resumo.erros)
        self.assertIn("token ausente", resumo.erros["mercado_livre"])

    def test_erro_inesperado_e_capturado(self):
        item = ItemWatchlist(nome="Fone TWS", termos="fone", fontes=("shopee",))

        def explode(termo, limite):
            raise ValueError("html mudou")

        with mock.patch("rotina_compras.rotina.obter", return_value=explode):
            resumo = coletar_item(item, pausa=0)

        self.assertEqual(resumo.ofertas, [])
        self.assertIn("html mudou", resumo.erros["shopee"])

    def test_preenche_o_item_na_oferta(self):
        item = ItemWatchlist(nome="Fone TWS", termos="fone", fontes=("shopee",))
        with mock.patch(
            "rotina_compras.rotina.obter",
            return_value=lambda t, l: [Oferta(item="", fonte="shopee", titulo="x", preco=10.0)],
        ):
            resumo = coletar_item(item, pausa=0)
        self.assertEqual(resumo.ofertas[0].item, "Fone TWS")

    def test_filtro_de_fontes_ativas(self):
        item = ItemWatchlist(nome="Fone TWS", termos="fone", fontes=("mercado_livre", "shopee"))
        chamadas = []

        def registrar_chamada(nome):
            chamadas.append(nome)
            return lambda t, l: []

        with mock.patch("rotina_compras.rotina.obter", side_effect=registrar_chamada):
            executar(Watchlist([item]), fontes_ativas=("shopee",), pausa=0)

        self.assertEqual(chamadas, ["shopee"])


class TestResumo(unittest.TestCase):
    def test_melhor_ignora_oferta_sem_preco(self):
        resumo = ResumoItem("Fone TWS", 150.0, [oferta(preco=None), oferta(preco=80.0)])
        self.assertEqual(resumo.melhor.preco, 80.0)

    def test_atingiu_alvo(self):
        self.assertTrue(ResumoItem("x", 100.0, [oferta(preco=99.0)]).atingiu_alvo)
        self.assertFalse(ResumoItem("x", 100.0, [oferta(preco=101.0)]).atingiu_alvo)
        self.assertFalse(ResumoItem("x", None, [oferta(preco=1.0)]).atingiu_alvo)

    def test_sem_oferta_nao_atinge_alvo(self):
        self.assertFalse(ResumoItem("x", 100.0, []).atingiu_alvo)

    def test_variacao_percentual(self):
        resumo = ResumoItem("x", None, [oferta(preco=80.0)], preco_anterior=100.0)
        self.assertAlmostEqual(resumo.variacao, -20.0)

    def test_variacao_sem_historico(self):
        self.assertIsNone(ResumoItem("x", None, [oferta(preco=80.0)]).variacao)


class TestHistorico(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self.pasta.name) / "dados" / "historico.jsonl"
        self.addCleanup(self.pasta.cleanup)

    def test_grava_apenas_o_melhor_por_item_e_fonte(self):
        historico.registrar(
            self.caminho,
            [oferta(preco=120.0), oferta(preco=90.0), oferta(fonte="shein", preco=70.0)],
        )
        linhas = self.caminho.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(linhas), 2)

    def test_minimo_acumulado_entre_execucoes(self):
        historico.registrar(self.caminho, [oferta(preco=120.0)])
        historico.registrar(self.caminho, [oferta(preco=95.0)])
        historico.registrar(self.caminho, [oferta(preco=110.0)])
        self.assertEqual(melhores := historico.melhores_anteriores(self.caminho), {"Fone TWS": 95.0})
        self.assertEqual(melhores["Fone TWS"], 95.0)

    def test_historico_inexistente(self):
        self.assertEqual(historico.melhores_anteriores(self.caminho), {})

    def test_linha_corrompida_e_ignorada(self):
        historico.registrar(self.caminho, [oferta(preco=100.0)])
        with self.caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write("{json quebrado\n")
        self.assertEqual(historico.melhores_anteriores(self.caminho), {"Fone TWS": 100.0})

    def test_ofertas_sem_preco_nao_geram_registro(self):
        historico.registrar(self.caminho, [oferta(preco=None)])
        self.assertFalse(self.caminho.exists())


class TestRelatorio(unittest.TestCase):
    def resumos(self):
        return [
            ResumoItem("Fone TWS", 150.0, [oferta(preco=99.9), oferta(fonte="shein", preco=None)],
                       preco_anterior=200.0),
            ResumoItem("Camiseta", 40.0, [], erros={"shein": "HTTP 429"}),
        ]

    def test_markdown_destaca_alvo_e_queda(self):
        texto = relatorio.gerar_markdown(self.resumos())
        self.assertIn("Bateram o preço-alvo", texto)
        self.assertIn("R$ 99,90", texto)
        self.assertIn("50% menor", texto)

    def test_markdown_mostra_erro_da_fonte(self):
        texto = relatorio.gerar_markdown(self.resumos())
        self.assertIn("HTTP 429", texto)
        self.assertIn("Nenhuma oferta encontrada", texto)

    def test_html_escapa_conteudo(self):
        resumo = ResumoItem("Fone <b>", None, [
            Oferta(item="Fone", fonte="shopee", titulo="Fone <script>", preco=10.0,
                   url="https://x.com/?a=1&b=2")
        ])
        html = relatorio.gerar_html([resumo])
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&amp;b=2", html)


if __name__ == "__main__":
    unittest.main()
