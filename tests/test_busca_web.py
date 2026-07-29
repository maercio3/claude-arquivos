import unittest
from unittest import mock

from rotina_compras.fontes import busca_web

HTML_DUCKDUCKGO = """
<html><body>
<div class="result results_links">
  <a rel="nofollow" class="result__a"
     href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fshopee.com.br%2Ffone-tws-i12&amp;rut=abc">
     Fone Bluetooth TWS i12 &ndash; Shopee</a>
  <a class="result__snippet">Compre Fone Bluetooth TWS i12 por R$ 49,90 com frete gr&aacute;tis.</a>
</div>
<div class="result results_links">
  <a rel="nofollow" class="result__a" href="https://outraloja.com.br/fone">Fone na outra loja</a>
  <a class="result__snippet">Apenas R$ 39,90.</a>
</div>
<div class="result results_links">
  <a rel="nofollow" class="result__a" href="https://www.shopee.com.br/fone-premium">Fone Premium</a>
  <a class="result__snippet">Sem pre&ccedil;o no trecho indexado.</a>
</div>
</body></html>
"""


class TestLeitorDuckDuckGo(unittest.TestCase):
    def setUp(self):
        leitor = busca_web._LeitorDuckDuckGo()
        leitor.feed(HTML_DUCKDUCKGO)
        leitor.close()
        self.resultados = leitor.resultados

    def test_le_todos_os_resultados(self):
        self.assertEqual(len(self.resultados), 3)

    def test_desembrulha_o_redirecionamento(self):
        self.assertEqual(self.resultados[0].url, "https://shopee.com.br/fone-tws-i12")

    def test_decodifica_entidades(self):
        self.assertIn("–", self.resultados[0].titulo)
        self.assertIn("grátis", self.resultados[0].trecho)

    def test_mantem_url_direta(self):
        self.assertEqual(self.resultados[1].url, "https://outraloja.com.br/fone")


class TestColetaPorLoja(unittest.TestCase):
    def _resultados(self):
        leitor = busca_web._LeitorDuckDuckGo()
        leitor.feed(HTML_DUCKDUCKGO)
        leitor.close()
        return leitor.resultados

    def test_filtra_por_dominio_da_loja(self):
        with mock.patch.object(
            busca_web, "buscar_na_web", return_value=self._resultados()
        ):
            ofertas = busca_web.buscar_shopee("fone tws", limite=5)

        self.assertEqual(len(ofertas), 2)  # outraloja.com.br fica de fora
        self.assertTrue(all(o.fonte == "shopee" for o in ofertas))
        self.assertEqual(ofertas[0].preco, 49.90)

    def test_subdominio_www_e_aceito(self):
        with mock.patch.object(
            busca_web, "buscar_na_web", return_value=self._resultados()
        ):
            ofertas = busca_web.buscar_shopee("fone tws", limite=5)
        self.assertEqual(ofertas[1].url, "https://www.shopee.com.br/fone-premium")

    def test_sem_preco_no_trecho_vira_none(self):
        with mock.patch.object(
            busca_web, "buscar_na_web", return_value=self._resultados()
        ):
            ofertas = busca_web.buscar_shopee("fone tws", limite=5)
        self.assertIsNone(ofertas[1].preco)

    def test_respeita_o_limite(self):
        with mock.patch.object(
            busca_web, "buscar_na_web", return_value=self._resultados()
        ):
            ofertas = busca_web.buscar_shopee("fone tws", limite=1)
        self.assertEqual(len(ofertas), 1)


class TestProvedor(unittest.TestCase):
    def test_provedor_desconhecido_falha_claro(self):
        with mock.patch.dict("os.environ", {"PROVEDOR_BUSCA": "bing"}):
            with self.assertRaises(busca_web.FonteIndisponivel):
                busca_web.buscar_na_web("fone", 3)


if __name__ == "__main__":
    unittest.main()
