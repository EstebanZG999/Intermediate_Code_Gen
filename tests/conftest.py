# tests/conftest.py
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Añade la raíz del repo al path (donde está la carpeta 'program')
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
