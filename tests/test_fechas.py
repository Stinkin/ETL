"""Conversión de fechas de texto (los formatos que entregan las fuentes)."""
import _setup
import unittest

import pandas as pd

from src.transform_fact_tabl import _to_datetime_text, _to_datetimeSD


def fechas(func, *valores):
    return list(func(pd.Series(list(valores))))


class TestFechasProject(_setup.Base):
    """_to_datetime_text: formato de MS Project, "Lun 27/04/26" (día de semana + dd/mm/aa)."""

    def test_con_y_sin_dia_de_semana(self):
        r = fechas(_to_datetime_text, "Lun 27/04/26", "27/04/26")
        self.assertEqual(r, [pd.Timestamp("2026-04-27")] * 2)

    def test_vacio_o_invalido_es_nat(self):
        r = fechas(_to_datetime_text, "", "NA", "xx")
        self.assertTrue(all(pd.isna(x) for x in r))


class TestFechasSD(_setup.Base):
    """_to_datetimeSD: '27/04/2026', '27/04/2026, 15:43', '27/04/26'."""

    def test_formatos_aceptados(self):
        r = fechas(_to_datetimeSD, "27/04/2026", "27/04/2026, 15:43", "27/04/26", "7/4/26")
        self.assertEqual(r, [pd.Timestamp("2026-04-27")] * 3 + [pd.Timestamp("2026-04-07")])

    def test_invalido_es_nat(self):
        r = fechas(_to_datetimeSD, "", "no es fecha", "31/02/2026")
        self.assertTrue(all(pd.isna(x) for x in r))


if __name__ == "__main__":
    unittest.main()
