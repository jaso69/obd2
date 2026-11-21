# CLAUDE.md — Toledo Diagnosis

Responde siempre en **español**. Documentación completa del proyecto (funciones,
hardware, protocolos, arquitectura, estado, guion de la web): **`docs/PROYECTO.md`**.
Léelo antes de cambios grandes o al empezar a trabajar en la web.

## Qué es
Programa de escritorio (Python + tkinter) para diagnosticar coches:
- **KKL · VAG KW1281** con cable KKL 409.1 FTDI: pensado para el SEAT Toledo II 1.9 TDI 2000 (Bosch EDC15), que no tiene OBD2 genérico.
- **ELM327 · OBD2 genérico** (USB o Bluetooth) para cualquier coche con OBD2.
- **Asistente IA** (Anthropic por defecto, OpenAI, DeepSeek) con diagnóstico guiado: la IA usa herramientas para leer averías/valores y pedir acciones al usuario.
- Simuladores de ambos adaptadores para probar sin coche.

## Usuario y entorno
- GitHub: `jaso69` → https://github.com/jaso69/obd2 (rama `main`).
- Desarrolla en **Windows** (`C:\Users\jose\Desktop\obd2`); la **web** la hará en **Fedora**.
- Pide pocas opciones y cosas que funcionen; prefiere que se pruebe antes de entregar.

## Comandos
- Ejecutar: `python gui.py` (Linux: `python3 gui.py`, requiere `python3-tkinter`).
- Pruebas de protocolo: `python tests/prueba_simuladores.py` (≈10 s, debe decir «TODO CORRECTO»).
- Ejecutable: Windows `build.bat` → `dist\ToledoDiagnosis.exe`; Linux `./build.sh` → `dist/ToledoDiagnosis`. Recompilar tras cambiar código.
- Autoprueba IA del ejecutable (sin gastar saldo): `ToledoDiagnosis --autotest-ia salida.txt`.
- Instalar en Linux: `./linux/instalar.sh`.

## Reglas al trabajar
- Probar contra los simuladores (y `tests/`) antes de dar algo por hecho; decir claramente qué no se ha podido probar (p. ej. coche real).
- **No** hacer consultas reales a la API de IA sin permiso (gastan saldo del usuario).
- **No** capturar el escritorio del usuario mientras trabaja.
- Las API keys nunca van al repositorio (se guardan en `%APPDATA%\ToledoDiagnosis` o `~/.config/ToledoDiagnosis`).
- Modelos Claude: por defecto `claude-opus-5-5` (ver `ia.py`).
- Commits con la línea `Co-Authored-By` que indique el sistema; en Windows el push lo suele lanzar el usuario (login interactivo de GitHub).

## Estado (2026-11-21)
v0.1.0 + soporte Linux. Todo probado con simuladores y la IA con la API real; **sin probar aún con coche real ni en un Linux real**. Licencia MIT (`LICENSE`). Release v0.1.0 publicada en GitHub (solo el .exe de Windows, sin Linux). Pendiente: release con binario Linux, web.
