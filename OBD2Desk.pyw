# Doble clic para abrir la interfaz grafica sin ventana de consola.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import gui

gui.main()
