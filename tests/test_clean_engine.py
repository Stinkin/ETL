"""Higiene de datos y mayúsculas (clean_engine.py)."""
import _setup
import unittest

import pandas as pd

from src.clean_engine import (capitalize_fields, capitalize_specific_words,
                              clean_up_columns, sanitize_dataframe)


class TestSanitize(_setup.Base):

    def test_texto_en_formato_titulo(self):
        """Clave para el resto del pipeline: después de la higiene todo es "No" / "Si", nunca "NO" / "SI"."""
        df = sanitize_dataframe(pd.DataFrame({"Proyecto": ["NO", "si", "  en   proceso "]}))
        self.assertEqual(list(df["Proyecto"]), ["No", "Si", "En Proceso"])

    def test_nulos_de_texto_pasan_a_vacio_y_numericos_a_cero(self):
        df = sanitize_dataframe(pd.DataFrame({"txt": ["a", None, "b"], "num": [1.0, 2.0, None]}))
        self.assertEqual(list(df["txt"]), ["A", "", "B"])
        self.assertEqual(list(df["num"]), [1.0, 2.0, 0.0])

    def test_quita_filas_vacias_y_duplicadas(self):
        df = sanitize_dataframe(pd.DataFrame({"a": ["x", "x", None], "b": [1, 1, None]}))
        self.assertEqual(len(df), 1)

    def test_limpia_espacios_en_los_encabezados(self):
        df = sanitize_dataframe(pd.DataFrame({"  Cod\xa0Proy. ": ["a"]}))
        self.assertEqual(list(df.columns), ["Cod Proy."])

    def test_no_modifica_el_original(self):
        original = pd.DataFrame({"a": ["NO"]})
        sanitize_dataframe(original)
        self.assertEqual(list(original["a"]), ["NO"])


class TestMayusculas(_setup.Base):

    def test_capitalize_fields_pone_en_mayuscula_las_columnas_definidas(self):
        data = {"DimProyecto": pd.DataFrame({"Cod Proy.": ["ab-1"], "Otra": ["xy"]})}
        out = capitalize_fields(data)
        self.assertEqual(out["DimProyecto"].loc[0, "Cod Proy."], "AB-1")
        self.assertEqual(out["DimProyecto"].loc[0, "Otra"], "xy")

    def test_siglas_en_mayuscula_solo_como_palabra_completa(self):
        data = {"DimProyecto": pd.DataFrame({"Nombre Proyecto": ["Migracion Sap y Bi", "Obsap Ovalo Aysa"]})}
        out = capitalize_specific_words(data)
        self.assertEqual(list(out["DimProyecto"]["Nombre Proyecto"]),
                         ["Migracion SAP y BI", "Obsap Ovalo AYSA"])

    def test_clean_up_columns_aplica_ambas_y_no_toca_el_original(self):
        data = {"DimProyecto": pd.DataFrame({"Cod Proy.": ["ab-1"], "Nombre Proyecto": ["Cierre sap"]})}
        out = clean_up_columns(data)
        self.assertEqual(out["DimProyecto"].loc[0, "Cod Proy."], "AB-1")
        self.assertEqual(out["DimProyecto"].loc[0, "Nombre Proyecto"], "Cierre SAP")
        self.assertEqual(data["DimProyecto"].loc[0, "Cod Proy."], "ab-1")    # el original queda igual


if __name__ == "__main__":
    unittest.main()
