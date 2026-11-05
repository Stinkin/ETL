"""Guardas: errores que ya ocurrieron una vez y la documentación contra el código.

No prueban datos: leen el código fuente y los documentos para detectar
cosas que se desincronizan sin que nadie lo note.
"""
import _setup
import ast
import re
import unittest

ROOT = _setup.ROOT
SRC_FILES = [ROOT / "main.py", *sorted((ROOT / "src").glob("*.py"))]


def parse(path):
    return ast.parse(path.read_text(encoding="utf-8-sig"))


def read_doc(name):
    return (ROOT / "docs" / name).read_text(encoding="utf-8-sig")


def documented_functions():
    """Nombres de la primera columna de las tablas de funciones (las que empiezan con '| Función')."""
    names, in_table = set(), False
    for line in read_doc("Modelo Modulos.md").splitlines():
        if line.startswith("| Funci"):
            in_table = True
        elif in_table and not line.startswith("|"):
            in_table = False
        elif in_table:
            m = re.match(r"^\|\s*`([A-Za-z_]\w*)`", line)
            if m:
                names.add(m.group(1))
    return names


def defined_functions():
    return {n.name for f in SRC_FILES for n in parse(f).body if isinstance(n, ast.FunctionDef)}


class TestCodigo(_setup.Base):

    def test_no_se_compara_contra_NO_ni_SI_en_mayusculas(self):
        """sanitize_dataframe deja todo el texto en formato Título ("No", "Si"):
        comparar contra "NO" o "SI" nunca coincide (fue el error del filtro de proyectos)."""
        found = [f"{f.name}, línea {n.lineno}: {n.value!r}"
                 for f in SRC_FILES for n in ast.walk(parse(f))
                 if isinstance(n, ast.Constant) and n.value in ("NO", "SI")]
        self.assertEqual(found, [], "Usar 'No' / 'Si'")

    def test_no_hay_anios_fijos_en_el_codigo(self):
        """Un año escrito a mano (ANIO_ACTUAL = 2026) deja de ser correcto el 1 de enero."""
        found = [f"{f.name}, línea {n.lineno}"
                 for f in SRC_FILES for n in ast.walk(parse(f))
                 if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                 and isinstance(n.value.value, int) and 2000 <= n.value.value <= 2100]
        self.assertEqual(found, [], "Usar date.today().year")


class TestDocumentacion(_setup.Base):

    def test_las_funciones_de_Modelo_Modulos_existen_en_el_codigo(self):
        documentadas = documented_functions()
        self.assertGreater(len(documentadas), 20, "No se pudieron leer las tablas de funciones")
        faltan = sorted(documentadas - defined_functions())
        self.assertEqual(faltan, [], "Documentadas en Modelo Modulos.md pero ausentes del código")

    def test_las_funciones_del_codigo_estan_en_Modelo_Modulos(self):
        doc = read_doc("Modelo Modulos.md")
        sin_documentar = sorted(n for n in defined_functions() if f"`{n}`" not in doc)
        self.assertEqual(sin_documentar, [], "Existen en el código pero no en Modelo Modulos.md")

    def test_cada_tabla_construida_tiene_seccion_en_Modelo_ETL(self):
        from src.transform_conf_dims import CONFORMED_BUILDERS
        from src.transform_fact_tabl import FACT_BUILDERS
        headings = set(re.findall(r"^#{2,4}\s+(\w+)\s*$", read_doc("Modelo ETL.md"), re.M))
        faltan = sorted((set(FACT_BUILDERS) | set(CONFORMED_BUILDERS)) - headings)
        self.assertEqual(faltan, [], "Se construyen en el código pero no tienen sección en Modelo ETL.md")


if __name__ == "__main__":
    unittest.main()
