# CLAUDE.md — OBD2Desk

Responde siempre en **español**. Documentación completa del proyecto (funciones,
hardware, protocolos, arquitectura, estado, guion de la web): **`docs/PROYECTO.md`**.
Léelo antes de cambios grandes o al empezar a trabajar en la web.

## Qué es
Programa de escritorio (Python + tkinter), en español e inglés, para diagnosticar coches.
Se llamaba *Toledo Diagnosis* hasta la v0.3.0; desde el 2026-11-27 es **OBD2Desk** (web https://obd2desk.com):
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
- Pruebas de protocolo: `python tests/prueba_simuladores.py` (≈20 s, debe decir «TODO CORRECTO»).
- Traducciones: `python tests/prueba_idioma.py` (≈1 s). **Todo texto visible va con `tr("texto en español")` y su traducción en `textos_en.py`** (ver `docs/PROYECTO.md` §7.6).
- Prueba de la GUI: `python tests/prueba_gui.py` (Linux: `xvfb-run -a .venv/bin/python tests/prueba_gui.py`, ≈90 s; el Python del sistema en Fedora no trae `pyserial`). En inglés: `OBD2DESK_IDIOMA=en ...` (busca restos de español). No lanzar las dos a la vez.
- Ejecutable: Windows `build.bat` → `dist\OBD2Desk.exe`; Linux `./build.sh` → `dist/OBD2Desk` (solo uso local). Recompilar tras cambiar código.
- Paquete Linux para publicar: `./linux/build-portable.sh vX.Y.Z` (contenedor Debian 11 con podman/docker) → `dist/OBD2Desk-vX.Y.Z-linux-x86_64.tar.gz`.
- Autoprueba IA del ejecutable (sin gastar saldo): `OBD2Desk --autotest-ia salida.txt`.
- Instalar en Linux: `./linux/instalar.sh`.
- Web (`web/`, ver `docs/PROYECTO.md` §12): capturas con `xvfb-run -a -s "-screen 0 2400x1500x24 -dpi 144" python3 web/capturas.py` (y `... capturas.py en` para las inglesas); ver en local con `python3 -m http.server -d web 8000`. Se publica en https://obd2desk.com con `./web/publicar.sh` (repo `jaso69/obd2desk`, Vercel). Español en `web/index.html`, inglés en `web/en/index.html`.

## Reglas al trabajar
- Probar contra los simuladores (y `tests/`) antes de dar algo por hecho; decir claramente qué no se ha podido probar (p. ej. coche real).
- **No** hacer consultas reales a la API de IA sin permiso (gastan saldo del usuario).
- **No** capturar el escritorio del usuario mientras trabaja.
- Las API keys nunca van al repositorio (se guardan en `%APPDATA%\OBD2Desk` o `~/.config/OBD2Desk`; la primera vez se copian de la carpeta antigua `ToledoDiagnosis`).
- Modelos Claude: por defecto `claude-opus-5-5` (ver `ia.py`).
- Commits con la línea `Co-Authored-By` que indique el sistema; en Windows el push lo suele lanzar el usuario (login interactivo de GitHub).

## Estado (2026-11-27)
**v0.3.0 publicada y cerrada** en GitHub («Latest», etiqueta `v0.3.0` → `5c83aa6`) con el `.exe` de Windows y el paquete Linux: escaneo de módulos VAG, tabla de averías VAG ampliada, datos congelados, monitores de preparación, averías permanentes, CALID/CVN, VIN decodificado, informe HTML, ELM327 WiFi y aviso de versión nueva. **Probada en coche: funciona bien**; falta probar un ELM327 WiFi real. Web al día (descargas de la v0.3.0, estado actualizado). Antes: v0.2.0 probada en un par de coches, Linux comprobado en Fedora 44 y en 7 distros, IA probada con la API real. Licencia MIT.

**v0.4.0 publicada y cerrada (2026-11-27, «Latest», etiqueta `v0.4.0` → `c10c53f`)**: renombrado a OBD2Desk e interfaz en inglés. Release con `OBD2Desk.exe` de Windows y el paquete Linux `OBD2Desk-v0.4.0-linux-x86_64.tar.gz`, ambos probados (instalan, migran la configuración de Toledo Diagnosis y abren). Web https://www.obd2desk.com publicada con las instrucciones nuevas (el dominio sin `www` redirige); los botones ya descargan la v0.4.0.

**Próximos pasos**: `docs/PROYECTO.md` §10 (pequeños pendientes → Bloque 2 de funciones para la v0.5.0 → más adelante). Pasos para sacar una versión: §8.3. La versión para Mac está aparcada.
