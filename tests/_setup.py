"""Configuración común de los tests. Cada archivo de test empieza con `import _setup`."""
import importlib.util
import os
import shutil
import sys
import tempfile
import types
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Los tests no leen archivos de MS Project: si win32com no está instalado, se simula
# solo para que `import src.extract_from_sources` no falle.
if importlib.util.find_spec("win32com") is None:
    fake = types.ModuleType("win32com")
    fake.client = types.ModuleType("win32com.client")
    sys.modules["win32com"] = fake
    sys.modules["win32com.client"] = fake.client


class Base(unittest.TestCase):
    """Base de todos los tests: silencia avisos de versiones de pandas que ensucian la salida."""

    def setUp(self):
        warnings.filterwarnings("ignore", message=".*select_dtypes.*")


class InTempDir(Base):
    """Ejecuta cada test dentro de una carpeta temporal.

    Varias funciones del pipeline escriben en `Data/` (auditoría) usando rutas relativas;
    así los tests nunca tocan la carpeta real del proyecto.
    """

    def setUp(self):
        super().setUp()
        self._old_cwd = os.getcwd()
        self.tmp = Path(tempfile.mkdtemp())
        os.chdir(self.tmp)
        os.makedirs("Data", exist_ok=True)

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)
