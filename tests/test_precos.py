import unittest

from rotina_compras.precos import extrair_preco, formatar, normalizar


class TestNormalizar(unittest.TestCase):
    def test_formato_brasileiro(self):
        self.assertEqual(normalizar("1.234,56"), 1234.56)
        self.assertEqual(normalizar("99,90"), 99.90)

    def test_milhar_sem_centavos(self):
        self.assertEqual(normalizar("1.234"), 1234.0)
        self.assertEqual(normalizar("12.345.678"), 12345678.0)

    def test_inteiro_simples(self):
        self.assertEqual(normalizar("99"), 99.0)

    def test_invalido(self):
        self.assertIsNone(normalizar(""))
        self.assertIsNone(normalizar("grátis"))


class TestExtrairPreco(unittest.TestCase):
    def test_dentro_de_frase(self):
        self.assertEqual(
            extrair_preco("Fone TWS por R$ 129,90 com frete grátis"), 129.90
        )

    def test_sem_espaco(self):
        self.assertEqual(extrair_preco("Oferta R$89,99 hoje"), 89.99)

    def test_valor_alto(self):
        self.assertEqual(extrair_preco("Notebook R$ 3.499,00 à vista"), 3499.00)

    def test_pega_o_primeiro(self):
        self.assertEqual(extrair_preco("De R$ 199,00 por R$ 149,00"), 199.00)

    def test_sem_preco(self):
        self.assertIsNone(extrair_preco("Consulte o valor no site"))
        self.assertIsNone(extrair_preco(""))


class TestFormatar(unittest.TestCase):
    def test_formata_em_reais(self):
        self.assertEqual(formatar(1234.5), "R$ 1.234,50")
        self.assertEqual(formatar(9.9), "R$ 9,90")

    def test_sem_valor(self):
        self.assertEqual(formatar(None), "—")


if __name__ == "__main__":
    unittest.main()
