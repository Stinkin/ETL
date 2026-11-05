"""Reglas de FactSeguimientoProyecto (ver docs/Modelo ETL.md).

Cada test arma una o dos filas de proyecto, corre la misma función que usa el pipeline
(`_process_proyect_files`) y verifica el resultado. Si cambia una regla en el código
o en el documento, el test que corresponda falla.
"""
import _setup
import unittest

import pandas as pd

from src.clean_engine import sanitize_dataframe
from src.transform_fact_tabl import _process_proyect_files

SNAPSHOT = "2026-05-15"

ESTADO = {"Sin Iniciar": 1, "En Proceso": 2, "Terminado": 3}
SITUACION = {"En Fecha": 1, "Demorado": 2, "Adelantado": 3}


def dims():
    return {
        "DimProyectoEstado": pd.DataFrame(
            {"KeyProyectoEstado": list(ESTADO.values()), "ProyectoEstado": list(ESTADO)}),
        "DimProyectoSituacion": pd.DataFrame(
            {"KeyProyectoSituacion": list(SITUACION.values()), "ProyectoSituacion": list(SITUACION)}),
    }


def project(code="P1", **changes):
    """Un proyecto "normal": en proceso al 50%, plan abril-junio, snapshot 15/05/2026."""
    row = {
        "Proyecto": "Si",
        "Cod Proy.": code,
        "FileDate": SNAPSHOT,
        "Comienzo_Programado": "Lun 01/04/26",
        "Fin_Programo": "Mar 30/06/26",
        "Comienzo": "Lun 01/04/26",
        "Fin": "",
        "Trabajo": "100 horas",
        "% trabajo completado": 0.5,
        "Cant. Reprogramaciones": 0,
    }
    row.update(changes)
    return row


def run(*rows):
    """Igual que en producción: primero la higiene (sanitize_dataframe) y después la regla."""
    raw = sanitize_dataframe(pd.DataFrame(list(rows)))
    result = _process_proyect_files({"Proyectos": raw, **dims()}, "test")
    return result.set_index("KeyProyecto") if not result.empty else result


class TestSituacion(_setup.InTempDir):
    """KeyProyectoSituacion: En Fecha por defecto, con excepciones según el estado."""

    CASES = [
        # (descripción, cambios sobre el proyecto base, situación esperada)
        ("sin iniciar, el inicio plan ya pasó",        dict(**{"% trabajo completado": 0}, Comienzo_Programado="01/05/26"), "Demorado"),
        ("sin iniciar, el inicio plan es futuro",      dict(**{"% trabajo completado": 0}, Comienzo_Programado="01/06/26"), "En Fecha"),
        ("sin iniciar y sin fecha de inicio plan",     dict(**{"% trabajo completado": 0}, Comienzo_Programado=""),         "En Fecha"),
        ("en proceso, el fin plan ya pasó",            dict(Fin_Programo="01/05/26"),                                       "Demorado"),
        ("en proceso, todavía no debía haber empezado", dict(Comienzo_Programado="01/06/26"),                               "Adelantado"),
        ("en proceso, dentro del plan",                dict(),                                                              "En Fecha"),
        ("terminado después del fin plan",             dict(**{"% trabajo completado": 1}, Fin="20/06/26", Fin_Programo="30/05/26"), "Demorado"),
        ("terminado antes del fin plan",               dict(**{"% trabajo completado": 1}, Fin="20/05/26", Fin_Programo="30/05/26"), "En Fecha"),
        ("terminado sin fecha de fin real",            dict(**{"% trabajo completado": 1}, Fin="", Fin_Programo="30/05/26"),         "En Fecha"),
    ]

    def test_reglas_de_situacion(self):
        for desc, changes, esperada in self.CASES:
            with self.subTest(desc):
                result = run(project(**changes))
                self.assertEqual(result.loc["P1", "KeyProyectoSituacion"], SITUACION[esperada])

    def test_situacion_desconocida_queda_en_cero(self):
        """Si la etiqueta no existe en DimProyectoSituacion la key es 0 (fallback documentado)."""
        raw = sanitize_dataframe(pd.DataFrame([project(Fin_Programo="01/05/26")]))   # sería "Demorado"
        d = dims()
        d["DimProyectoSituacion"] = d["DimProyectoSituacion"].query("ProyectoSituacion != 'Demorado'")
        result = _process_proyect_files({"Proyectos": raw, **d}, "test")
        self.assertEqual(result.iloc[0]["KeyProyectoSituacion"], 0)


class TestEstado(_setup.InTempDir):
    """KeyProyectoEstado: por porcentaje si Proyecto = "Si", explícito en otro caso."""

    def test_estado_por_porcentaje(self):
        casos = [(0, "Sin Iniciar"), (0.5, "En Proceso"), (1, "Terminado"),
                 (50, "En Proceso"), (100, "Terminado")]       # 50 y 100 vienen en escala 0-100
        for pct, esperado in casos:
            with self.subTest(pct=pct):
                result = run(project(**{"% trabajo completado": pct}))
                self.assertEqual(result.loc["P1", "KeyProyectoEstado"], ESTADO[esperado])

    def test_estado_explicito_ignora_el_porcentaje(self):
        casos = [("Terminado", 0), ("En Proceso", 0), ("Sin Iniciar", 1)]
        for estado, pct in casos:
            with self.subTest(estado=estado):
                result = run(project(Proyecto=estado, **{"% trabajo completado": pct}))
                self.assertEqual(result.loc["P1", "KeyProyectoEstado"], ESTADO[estado])

    def test_situacion_usa_el_estado_explicito(self):
        """Estado explícito "En Proceso" con el fin plan vencido => Demorado, aunque el avance sea 0."""
        result = run(project(Proyecto="En Proceso", Fin_Programo="01/05/26", **{"% trabajo completado": 0}))
        self.assertEqual(result.loc["P1", "KeyProyectoSituacion"], SITUACION["Demorado"])


class TestFiltroProyecto(_setup.InTempDir):
    """Solo se procesan filas con Proyecto distinto de "No" y no vacío."""

    def test_se_descartan_no_y_vacios(self):
        result = run(project("P1"), project("P2", Proyecto="No"), project("P3", Proyecto=""))
        self.assertEqual(list(result.index), ["P1"])

    def test_no_en_mayusculas_tambien_se_descarta(self):
        """Regresión del typo "NO" vs "No": la higiene pasa todo a formato Título, el filtro debe verlo."""
        result = run(project("P1"), project("P2", Proyecto="NO"))
        self.assertEqual(list(result.index), ["P1"])

    def test_si_todo_se_descarta_devuelve_tabla_vacia(self):
        result = run(project("P1", Proyecto="No"))
        self.assertTrue(result.empty)


class TestMetricasYFechas(_setup.InTempDir):

    def test_horas_planificadas(self):
        casos = [("1.187,51 horas", 1188), ("40 horas", 40), ("8 horas", 8), ("", 0), ("abc", 0)]
        for trabajo, esperado in casos:
            with self.subTest(trabajo=trabajo):
                result = run(project(Trabajo=trabajo))
                self.assertEqual(result.loc["P1", "HorasPlanificadas"], esperado)

    def test_porcentaje_de_avance(self):
        casos = [(0.456, 0.46), (50, 0.5), (1, 1.0), (100, 1.0), (0, 0.0)]
        for pct, esperado in casos:
            with self.subTest(pct=pct):
                result = run(project(**{"% trabajo completado": pct}))
                self.assertAlmostEqual(result.loc["P1", "PorcentajeDeAvance"], esperado)

    def test_fechas(self):
        result = run(project(Fin="Vie 03/07/26"))
        fila = result.loc["P1"]
        self.assertEqual(fila["FechaSnapshot"], pd.Timestamp("2026-05-15"))
        self.assertEqual(fila["FechaInicioPlan"], pd.Timestamp("2026-04-01"))
        self.assertEqual(fila["FechaFinPlan"], pd.Timestamp("2026-06-30"))
        self.assertEqual(fila["FechaFinReal"], pd.Timestamp("2026-07-03"))

    def test_columnas_de_salida(self):
        """Contrato con Power BI: estas columnas, en este orden."""
        result = _process_proyect_files(
            {"Proyectos": sanitize_dataframe(pd.DataFrame([project()])), **dims()}, "test")
        self.assertEqual(list(result.columns), [
            "KeyProyecto", "FechaSnapshot", "FechaInicioPlan", "FechaFinPlan", "FechaInicioReal",
            "FechaFinReal", "PorcentajeDeAvance", "HorasPlanificadas", "CantidadReplanificaciones",
            "KeyProyectoEstado", "KeyProyectoSituacion"])


if __name__ == "__main__":
    unittest.main()
