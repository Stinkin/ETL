"""Carga a parquet: limpieza previa y comportamiento ante errores."""
import _setup
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from src.load_to_parquet import clear_parquets, load_all_to_parquet


def fake_to_parquet(self, path, **kwargs):
    """Escritor falso (no hace falta pyarrow para probar la lógica). Falla si la tabla tiene la columna 'boom'."""
    if "boom" in self.columns:
        raise ValueError("tabla que no se puede guardar")
    Path(path).write_bytes(b"x")


class TestClearParquets(_setup.InTempDir):

    def crear(self, *nombres):
        out = self.tmp / "processed"
        out.mkdir(exist_ok=True)
        for n in nombres:
            (out / n).write_bytes(b"x")
        return out

    def nombres(self, carpeta):
        return sorted(p.name for p in carpeta.iterdir())

    def test_borra_parquets_y_conserva_bajadaproyectos(self):
        out = self.crear("DimA.parquet", "FactB.parquet", "bajadaproyectos.parquet")
        clear_parquets(out)
        self.assertEqual(self.nombres(out), ["bajadaproyectos.parquet"])

    def test_conserva_bajadaproyectos_con_cualquier_combinacion_de_mayusculas(self):
        out = self.crear("BajadaProyectos.parquet", "DimA.parquet")
        clear_parquets(out)
        self.assertEqual(self.nombres(out), ["BajadaProyectos.parquet"])

    def test_no_toca_archivos_que_no_son_parquet(self):
        out = self.crear("DimA.parquet", "notas.txt")
        clear_parquets(out)
        self.assertEqual(self.nombres(out), ["notas.txt"])

    def test_carpeta_inexistente_no_falla(self):
        clear_parquets(self.tmp / "no_existe")

    def test_archivo_bloqueado_detiene_la_corrida(self):
        """Si Power BI tiene un archivo abierto, no se sigue (evita mezclar archivos viejos y nuevos)."""
        out = self.crear("DimA.parquet")
        with mock.patch.object(Path, "unlink", side_effect=PermissionError):
            with self.assertRaises(SystemExit):
                clear_parquets(out)
        self.assertEqual(self.nombres(out), ["DimA.parquet"])


@mock.patch.object(pd.DataFrame, "to_parquet", fake_to_parquet)
class TestLoadAll(_setup.InTempDir):

    def test_escribe_un_archivo_por_tabla(self):
        out = self.tmp / "processed"
        load_all_to_parquet({"DimA": pd.DataFrame({"a": [1]}), "FactB": pd.DataFrame({"a": [1]})}, str(out))
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["DimA.parquet", "FactB.parquet"])

    def test_una_tabla_que_falla_no_frena_a_las_demas(self):
        out = self.tmp / "processed"
        datos = {"DimA": pd.DataFrame({"a": [1]}), "Mala": pd.DataFrame({"boom": [1]}), "FactB": pd.DataFrame({"a": [1]})}
        load_all_to_parquet(datos, str(out))
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["DimA.parquet", "FactB.parquet"])

    def test_sin_tablas_no_falla(self):
        load_all_to_parquet({}, str(self.tmp / "processed"))


if __name__ == "__main__":
    unittest.main()
