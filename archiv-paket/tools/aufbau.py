"""Legt die Ordnerstruktur an (aendert nichts an vorhandenen Dateien).
Aufruf:  python tools/aufbau.py [ARCHIV_WURZEL]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import ORDNER

wurzel = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
for o in ORDNER:
    os.makedirs(os.path.join(wurzel, o), exist_ok=True)
    print("ok", o)
