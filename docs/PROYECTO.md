# Toledo Diagnosis — Documentación completa del proyecto

Documento de referencia para (1) crear la web del programa y (2) retomar el
desarrollo en cualquier equipo sin tener que volver a explicar el proyecto.
Última actualización: 2026-11-21 (versión del código: v0.1.0 + soporte Linux y paquete portable).

- Repositorio: https://github.com/jaso69/obd2 (rama `main`)
- Autor: jaso69
- Licencia: **MIT** (archivo `LICENSE`, © 2026 jaso69). Permite usar, copiar, modificar y redistribuir, también comercialmente, manteniendo el aviso de copyright; sin garantía.

---

## 1. Qué es

**Toledo Diagnosis** es un programa de escritorio (Windows y Linux) para
diagnosticar coches desde un portátil:

- Nació para un **SEAT Toledo II 1.9 TDI del año 2000** (centralita Bosch EDC15),
  que **no tiene OBD2 genérico** y habla el protocolo propietario de VAG
  **KW1281** por línea K. Para eso se usa un **cable KKL 409.1 con chip FTDI**.
- También funciona como **lector OBD2 genérico** con un **ELM327** (USB o
  Bluetooth) para cualquier coche con OBD2/EOBD.
- Incluye un **asistente de IA** (Claude de Anthropic por defecto, u OpenAI o
  DeepSeek) que, a partir de la descripción de un síntoma, **lee él mismo averías
  y valores del coche, pide al usuario que haga cosas (arrancar, acelerar…) y da
  un diagnóstico razonado**.
- Interfaz gráfica oscura con relojes, gráficas en tiempo real, tablas, averías y
  grabación a CSV. Se distribuye como **ejecutable de un solo archivo**.
- Trae **simuladores** del cable+centralita y del ELM327+coche para probar todo sin coche.

Mensaje corto para la web: *«Diagnóstico de tu coche desde el portátil: averías,
valores en directo y un asistente de IA que hace las comprobaciones por ti. Para
VAG antiguos con cable KKL y cualquier coche con OBD2.»*

---

## 2. Funcionalidades (por pestaña de la interfaz)

Cabecera: selector **Conexión** (KKL · VAG KW1281 / ELM327 · OBD2 genérico),
**Puerto** (detecta el cable FTDI o el Bluetooth; incluye «Simulador (sin coche)»),
**Módulo** (solo KKL: 01 motor, 02 cambio, 03 ABS, 08 clima, 15 airbag, 17 cuadro,
35 cierre, 56 radio) y botón **Conectar/Desconectar**. Indicador de estado.

| Pestaña | Modo KKL (VAG KW1281) | Modo ELM327 (OBD2) |
|---|---|---|
| **Panel** | Relojes: rpm, caudal inyectado (mg/H), presión turbo (con marca de presión teórica), refrigerante. Tarjetas: ciclo N75, ciclo EGR, tensión dosificador, masa de aire. Gráficas 60 s: turbo teórico/real (G011) y masa de aire teórica/real (G003). | Relojes: rpm, velocidad, refrigerante, carga. Tarjetas: temp. admisión, MAF, mariposa, tensión. Gráficas: rpm y carga/mariposa. |
| **Valores medidos** | Grupos de valores medidos (casillas con los típicos de EDC15 + campo para otros). Tabla en vivo. Botón **Grabar CSV**. | Lista con solo los PIDs que el coche soporta (selección múltiple). Tabla en vivo. Grabar CSV. |
| **Averías** | Códigos VAG de 5 cifras, componente, tipo de fallo, intermitente. Leer / Borrar (con confirmación). | Códigos P0xxx memorizados y pendientes con descripción, estado del testigo MIL. Leer / Borrar. |
| **Vehículo** | Identificación de la centralita (referencia, componente, software, codificación), velocidad, keywords, eco del cable. | Adaptador, protocolo, VIN, tensión de batería, estándar OBD, MIL, nº de PIDs. |
| **✦ Asistente IA** | Igual en ambos modos (ver §6). | |
| **Registro** | Historial de la comunicación; opción de depuración que muestra cada bloque/comando. | |

Otros detalles:
- Los CSV se guardan junto al ejecutable (`log_AAAAMMDD_HHMMSS.csv`, separador `;`, coma decimal: se abren directamente en Excel/LibreOffice).
- La sesión KW1281 se mantiene viva sola mientras estás en el menú (keep-alive).
- Si se pierde la conexión, se avisa y se puede reconectar.
- Versión de consola alternativa: `toledo.py` (menú de texto, solo KKL).
- `sonda_toledo.py`: script de diagnóstico para comprobar qué responde una centralita a un ELM327 (OBD2 genérico, keywords del init de 5 baudios, KWP2000 a la dirección 0x01).

---

## 3. Vehículos y hardware

### 3.1 El coche objetivo: SEAT Toledo II 1.9 TDI (2000)
- Plataforma Toledo II (1M). Motores 1.9 TDI: AHF/ASV (110 CV), ALH/AGR (90 CV) con bomba rotativa y **Bosch EDC15V**; ARL (150 CV) con inyector-bomba y EDC15P.
- En Europa el EOBD solo fue obligatorio en diésel desde 2003-2004 → **un TDI del 2000 normalmente no responde a OBD2 genérico**. El conector de 16 pines existe, pero la centralita habla **KW1281** (VAG) por la **línea K (pin 7)**.
- El **ELM327 no sirve para KW1281** (no hace la confirmación byte a byte por complemento). Solo funcionaría si la centralita aceptara KWP2000 (algunas EDC15 más modernas): eso lo comprueba `sonda_toledo.py`.
- Conector OBD: bajo el salpicadero, lado del conductor.
- Problema conocido: una radio no original puede bloquear la línea K; desconectarla para probar.

### 3.2 Qué cable comprar (guía para la web)
**Para VAG hasta ~2004 (KW1281): cable «KKL VAG-COM 409.1» con chip FTDI FT232RL/FT232RQ.**
- Conexión USB. Unos 10-20 €.
- **Evitar chips CH340/CH341/PL2303** (el init de 5 baudios necesita el control de la señal *break* que FTDI hace bien). En Windows: Administrador de dispositivos → Id. de hardware debe ser `VID_0403&PID_6001` (FTDI); `VID_1A86` = CH340.
- Muchos cables baratos llevan FTDI falsos; algunos drivers oficiales los rechazan (el puerto aparece pero no comunica). Se suele arreglar con un driver anterior.
- Cables con **interruptor Fiat de 4 posiciones** (KKL 409.1 + Fiat ECU Scan): válidos; usar la **posición 1** para VAG (línea K al pin 7). Si no responde, probar las otras.
- **No sirven** para este uso: ELM327 con interruptor HS-CAN/MS-CAN (son para Ford/FORScan; el FTDI va al chip ELM, no a la línea K). **No recomendado**: «VAG K+CAN Commander 1.4» (pensado para inmovilizador/llaves, la parte K-line no está garantizada; su limitación «solo Windows XP/7 32 bits» es de su software, no del driver).
- Inalámbrico para KW1281 no existe de serie (Bluetooth/WiFi añaden latencia). Alternativa futura: ESP32 + transceptor L9637D/MC33290 haciendo el KW1281 en firmware.

**Para cualquier coche con OBD2: ELM327** (USB, o Bluetooth clásico SPP).
- Bluetooth: emparejar en el sistema; en Windows aparece como puerto COM (Windows crea dos; uno funciona). En Linux hay que enlazarlo como `/dev/rfcomm0` (ver §4.2).
- Los ELM327 solo BLE (algunos para iPhone) **no** están soportados (no crean puerto serie).
- Muchos clones dicen «v2.1» y son v1.0 incompletos; si falla algún comando, el programa lo tolera en lo posible.

---

## 4. Instalación y primer uso

### 4.1 Windows (10/11, 64 bits)
- **Ejecutable**: `ToledoDiagnosis.exe` (≈26 MB, un solo archivo). Se genera con `build.bat` en `dist\`. No necesita Python.
- SmartScreen avisará la primera vez (no está firmado): «Más información → Ejecutar de todas formas».
- Cable FTDI: el driver lo instala Windows Update (si no, driver VCP de FTDI). **Poner la latencia a 1 ms**: Administrador de dispositivos → Puertos → USB Serial Port → Propiedades → Configuración de puerto → Opciones avanzadas → Temporizador de latencia = 1. Es por equipo: repetir en cada PC.
- Desde código: `pip install -r requirements.txt` y `python gui.py` (o doble clic en `Toledo Diagnosis.pyw`).

### 4.2 Linux (comprobado en Fedora 44 y en contenedores de 7 distros, ver §11)
- Requisitos para ejecutar desde código: Python 3.10+ y tkinter.
  - Fedora: `sudo dnf install python3 python3-tkinter`
  - Debian/Ubuntu: `sudo apt install python3 python3-venv python3-tk`
  - Luego: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python gui.py`
- **Ejecutable local**: `./build.sh` genera `dist/ToledoDiagnosis` (binario único con PyInstaller, usa un venv `.venv`). Solo vale para distros con una glibc igual o más nueva que la del equipo donde se compila (compilado en Fedora 44 no arranca en Ubuntu 22.04).
- **Para distribuir**: `./linux/build-portable.sh [versión]` compila dentro de un contenedor Debian 11 (podman o docker, imagen `python:3.13-bullseye`, glibc 2.31), pasa la autoprueba de IA y genera `dist/ToledoDiagnosis-<versión>-linux-x86_64.tar.gz` con: `ToledoDiagnosis`, `instalar.sh`, `toledo-diagnosis.desktop`, `icono.png`, `LEEME.txt` (`linux/LEEME.txt`) y `LICENSE`. Funciona en Ubuntu 20.04+, Debian 11+, Mint 20+, Fedora, openSUSE, Arch.
- **Instalar en el menú**: `./instalar.sh [ejecutable]` (desde el paquete) o `./linux/instalar.sh` (desde el repositorio) → copia a `~/.local/bin`, icono y lanzador `.desktop` (sin sudo). `--desinstalar` lo quita (deja la configuración).
- **Permisos del puerto serie**: `sudo usermod -aG dialout $USER` (en Arch el grupo es `uucp`) y cerrar sesión. Sin esto sale «Permission denied»; el programa y el instalador detectan el grupo del puerto y dicen el comando exacto.
- **brltty** (Ubuntu/Mint): el lector braille captura adaptadores USB-serie (CH340, a veces FTDI) y `/dev/ttyUSB0` desaparece. Solución: `sudo apt remove brltty`. El instalador avisa si está.
- **Lanzador**: Tk pone la clase de ventana `Toledodiagnosis` (capitaliza `className`), por eso `StartupWMClass=Toledodiagnosis` en el `.desktop`; si no coincide, el dock muestra un icono genérico duplicado.
- **CSV**: con el binario van a `Documentos/ToledoDiagnosis` (`xdg-user-dir DOCUMENTS`); desde el código, junto a `gui.py`. En Windows, junto al `.exe`.
- Puertos: cable FTDI = `/dev/ttyUSB0`; ELM327 USB = `/dev/ttyUSB0` o `/dev/ttyACM0`; ELM327 Bluetooth: `bluetoothctl` (pair, trust) y `sudo rfcomm bind 0 AA:BB:CC:DD:EE:FF` → `/dev/rfcomm0`.
- Latencia FTDI: en Linux el programa activa el modo de baja latencia automáticamente (`set_low_latency_mode`), equivalente a poner 1 ms.
- Clave de IA en `~/.config/ToledoDiagnosis/config.json` con permisos 600 (no cifrada; en Windows va cifrada con DPAPI).
- Fuentes: elige automáticamente Noto Sans / Cantarell / DejaVu Sans / Liberation según lo instalado.

### 4.3 Primeros pasos (guía de uso para la web)
1. Probar sin coche: Puerto «Simulador (sin coche)», Conectar, pestaña Panel → «Iniciar lectura».
2. En el coche: contacto puesto (motor parado vale para leer averías), conectar el cable al OBD y al portátil, elegir Conexión y Puerto, **Conectar**. KKL tarda 2-6 s (init a 5 baudios y prueba de velocidades); ELM327 hasta 25 s (búsqueda de protocolo).
3. Pestaña **Averías → Leer averías**. Anotar antes de borrar.
4. **Panel** para ver en vivo; **Valores medidos** para elegir grupos/PIDs y **Grabar CSV**.
5. **✦ Asistente IA**: describir el problema y dejar que la IA haga las comprobaciones.

---

## 5. Grupos VAG útiles (1.9 TDI EDC15, orientativo)

| Grupo | Contenido típico |
|---|---|
| 001 | Régimen, caudal inyectado (mg/H), tensión dosificador/émbolo, temp. refrigerante |
| 002 | Régimen, pedal acelerador, estado de funcionamiento, temp. refrigerante |
| 003 | Régimen, masa de aire teórica, masa de aire real, ciclo válvula EGR |
| 004 | Régimen, comienzo de inyección teórico/real, ciclo válvula (bomba rotativa) |
| 007 | Temperaturas (combustible, refrigerante…) |
| 008 | Régimen, caudal solicitado, limitaciones por régimen y por masa de aire |
| 010 | Masa de aire, presión atmosférica, presión colector, pedal |
| 011 | Régimen, presión de turbo teórica, presión real, ciclo N75 |
| 013 | Marcha suave por cilindro (si existe) |

Los nombres de campo son orientativos; la unidad la calcula el programa con la
fórmula que envía la propia centralita.

---

## 6. Asistente de IA

### 6.1 Qué hace
- **Diagnóstico guiado**: el usuario describe el síntoma («le falta potencia y echa humo negro»). La IA plantea hipótesis y usa herramientas:
  - `estado_conexion` — modo, conexión, datos de la centralita, grupos/PIDs disponibles.
  - `leer_averias` — también actualiza la pestaña Averías.
  - `leer_valores` — grupos VAG (máx. 4) o PIDs OBD2 (máx. 10), 1-40 muestras con intervalo 0-5 s (series para acelerones, calentamientos…).
  - `pedir_accion_usuario` — ventana no modal con la instrucción y botones **Hecho** / **No puedo** + comentario.
  - `borrar_averias` — siempre con confirmación del usuario.
  - `leer_registro` — últimas líneas del registro (diagnóstico de problemas de conexión).
- Botones: «Analizar averías del vehículo», «Analizar errores del programa», «Nueva conversación», «Detener». Preguntas de seguimiento en el chat.
- En el chat se ve cada paso (⚙ Leyendo grupos 3, 11 · 15 muestras…) y la respuesta en streaming con formato.
- Límite: **15 rondas de herramientas por mensaje**; después debe concluir (en la última ronda se fuerza `tool_choice: none`).
- **Seguridad en el prompt**: prefiere pruebas en parado; nunca pide mirar la pantalla conduciendo; pruebas en marcha solo con acompañante; avisa de correas/ventilador; borra averías solo si aporta.
- Respuesta final: conclusión, causas por probabilidad con evidencia, siguientes pasos de lo barato a lo caro, si se puede circular.

### 6.2 Proveedores y claves
| Proveedor | Modelo por defecto | SDK | Dónde sacar la clave |
|---|---|---|---|
| Anthropic (Claude) — por defecto | `claude-opus-5-5` | `anthropic` | https://platform.claude.com/settings/keys |
| OpenAI | `gpt-5` (editable; no verificado que exista ese nombre) | `openai` | https://platform.openai.com/api-keys |
| DeepSeek | `deepseek-chat` | `openai` con `base_url=https://api.deepseek.com` | https://platform.deepseek.com/api_keys |

- La clave la pone cada usuario (cada uno paga su consumo). Coste orientativo con Claude Opus 5.5: céntimos por consulta; un diagnóstico guiado con ~10 comprobaciones ≈ 0,05-0,20 €.
- Con Claude Opus 5.5/Sonnet 5.5 se usa `effort: medium` y el reintento automático en otro modelo si el modelo declina (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`).
- **Privacidad (poner en la web)**: se envían al proveedor elegido los datos del vehículo (incluido el VIN), las averías, los valores medidos y, si se pide, el registro del programa. La clave se guarda solo en el equipo del usuario.
- Probado con una consulta real de Claude contra el simulador (diagnóstico completo en ~52 s con 11 llamadas a herramientas).

---

## 7. Arquitectura técnica

### 7.1 Archivos
| Archivo | Función |
|---|---|
| `gui.py` | Interfaz tkinter/ttk (clase `App`), hilo de comunicación (`Worker`), widgets `Gauge` y `Chart`, pestaña de IA y ejecución de sus herramientas. Opción oculta `--autotest-ia <fichero>`. |
| `kw1281.py` | Protocolo KW1281: init 5 baudios por *break*, detección de velocidad, eco, complementos, bloques, keep-alive en hilo, averías, borrado, grupos. |
| `vag_datos.py` | Fórmulas de valores medidos VAG (≈60), tipos de fallo, averías VAG de 5 cifras (tabla pequeña), grupos EDC15, módulos. |
| `elm327.py` | OBD2 por ELM327: inicialización, protocolo automático, parseo con cabeceras (CAN 11/29 bits y línea K), reensamblado ISO-TP, multi-PID, averías (03/07/04), VIN (09 02), MIL, tensión. |
| `obd_datos.py` | PIDs del modo 01 (≈50) con decodificadores, estándares OBD, descripciones de averías P0xxx (≈110). |
| `ia.py` | Proveedores, configuración y claves, `Conversacion` (bucle de herramientas para Anthropic y OpenAI/DeepSeek), prompt de sistema, definición de herramientas. |
| `simulador.py` | `FakeSerial` (cable KKL + EDC15 a 9600 bd, decodifica el init de 5 baudios por tiempos reales) y `FakeELMSerial` (ELM327 + coche gasolina CAN 11/500). |
| `toledo.py` | Versión consola KKL (y utilidades reutilizadas por la GUI: `leer_grupo_formateado`, `texto_id`). |
| `sonda_toledo.py` | Sonda de protocolos con ELM327 para el Toledo. |
| `tests/prueba_simuladores.py` | 17 comprobaciones de protocolo contra los simuladores (`python tests/prueba_simuladores.py`). |
| `tests/prueba_gui.py` | Maneja la ventana real con los dos simuladores: conectar, averías, panel, valores + CSV, configuración IA (`xvfb-run -a python3 tests/prueba_gui.py` en Linux). |
| `build.bat` / `build.sh` | Ejecutable único con PyInstaller (Windows / Linux). |
| `linux/build-portable.sh` | Binario Linux portable (contenedor Debian 11) y paquete `.tar.gz` para distribuir. |
| `linux/instalar.sh`, `linux/toledo-diagnosis.desktop`, `linux/LEEME.txt` | Instalación de usuario en Linux y LÉEME del paquete. |
| `crear_icono.py` | Genera `icono.ico`/`icono.png` con Pillow (solo desarrollo). |
| `Toledo Diagnosis.pyw` | Lanzador sin consola en Windows. |

### 7.2 Hilos
- **Hilo principal (Tk)**: interfaz. Sondea una cola cada 50 ms (`App.poll`).
- **Worker**: único hilo que habla con el puerto serie. Recibe tareas (`connect`, `disconnect`, `dtcs`, `clear`, `live`, `debug`, `tool`) y publica eventos (`connected`, `live`, `dtcs`, `lost`, `error`, `log`…). Las lecturas en vivo llevan un número de generación para descartar datos de lecturas anteriores.
- **KW1281 keep-alive**: hilo dentro de `KW1281` que intercambia bloques ACK cuando nadie usa la sesión (con `RLock`).
- **Hilo de IA** por consulta: ejecuta `Conversacion.enviar`; las herramientas del coche van al Worker (tarea `tool` + cola de respuesta) y las de interfaz al hilo Tk (evento `ai_main`). Cada conversación tiene un número para descartar respuestas tras «Nueva conversación».

### 7.3 KW1281 (resumen)
- Init: dirección del módulo (0x01 motor) a 5 baudios, 7 bits + paridad impar, generada con `break_condition` (start, 8 bits LSB primero, stop; 200 ms por bit).
- La ECU responde a su velocidad (se prueban 10400 y 9600): `0x55` + keywords `01 8A` (= 1281). El tester responde `0xFF ^ KW2` (0x75) a los 25-50 ms. Si las keywords indican KWP2000, se avisa.
- Bloques: `[longitud][contador][título][datos…][0x03]`; cada byte salvo el 0x03 lo confirma el receptor con su complemento. Contador +1 por bloque en ambos sentidos. Línea K half-duplex: todo lo enviado vuelve como eco (se detecta si el cable no hace eco).
- Títulos: 0x09 ACK, 0x0A NAK, 0x06 fin, 0x05 borrar averías, 0x07 leer averías → 0xFC, 0x29 leer grupo → 0xE7, 0xF6 texto ASCII (identificación).
- Averías: tripletes (código alto, bajo, estado); estado & 0x7F = tipo de fallo, bit 0x80 = intermitente; `FF FF 88` = sin averías.
- Grupos: tripletes (fórmula, a, b) → valor y unidad según `vag_datos.FORMULAS`.

### 7.4 ELM327 (resumen)
- `ATZ, ATE0, ATL0, ATS1, ATH1, ATAT1, ATSP0`, luego `0100` (búsqueda, hasta 25 s), `ATDPN`/`ATDP`. Prueba velocidades 38400/9600/115200/57600 (en Bluetooth da igual).
- Si `ATSP0` + `0100` no da respuesta, fuerza uno a uno los protocolos de línea K: `ATSP5` (KWP2000 rápido), `ATSP4` (KWP2000 lento) y `ATSP3` (ISO 9141-2), con `ATPC` entre medias y dos `0100` por protocolo (12 s cada uno). Si ninguno responde, vuelve a `ATSP0` y da un error que explica las causas (coche sin OBD2 real, clon malo). Pensado para Mercedes y otros coches anteriores a CAN. El simulador lo reproduce con `FakeELMSerial(protocolo, auto_falla=True)`.
- Con cabeceras activadas: separa centralitas (prefiere 7E8 o 10/11) y reensambla ISO-TP (tramas 0x/1x/2x). Línea K: cabecera de 3 bytes + checksum (KWP2000 también con cabecera de 4 bytes, longitud aparte).
- Multi-PID (hasta 6 por petición) solo en CAN; si falla, pasa a PID a PID.

### 7.5 Estilo visual (para la web)
- Tema oscuro. Colores: fondo `#111418`, panel `#181c22`, tarjeta `#1f242c`, tarjeta 2 `#262c36`, pista `#2f3642`, texto `#e8ebf0`, texto secundario `#8a93a2`, **acento naranja `#ff7a29`**, azul `#4aa8ff`, ok `#3ccf7a`, aviso `#f5b83d`, error `#ef5350`.
- Fuentes: Segoe UI (Windows), Noto Sans (Linux).
- Icono: reloj de turbo naranja con aguja y texto «TDI» sobre cuadrado oscuro redondeado (`icono.png` 256 px, `icono.ico` multi-tamaño).

---

## 8. Compilar, versionar y publicar
- Windows: `build.bat` → `dist\ToledoDiagnosis.exe`. Linux: `./build.sh` → `dist/ToledoDiagnosis` (uso local); para publicar, `./linux/build-portable.sh vX.Y.Z` → `dist/ToledoDiagnosis-vX.Y.Z-linux-x86_64.tar.gz`.
- Tras cambiar código, recompilar y copiar el ejecutable nuevo.
- Comprobación rápida del ejecutable (sin gastar saldo): `ToledoDiagnosis --autotest-ia salida.txt` → debe poner «API key … no válida» para los 3 proveedores (confirma que los SDK y HTTPS funcionan dentro del binario).
- Git: etiqueta `v0.1.0` en el commit inicial `a354d67`. **Release v0.1.0 publicada** (pre-release) con `ToledoDiagnosis.exe` de Windows compilado desde esa etiqueta: https://github.com/jaso69/obd2/releases/tag/v0.1.0 — descarga directa: https://github.com/jaso69/obd2/releases/download/v0.1.0/ToledoDiagnosis.exe
- La v0.1.0 **no incluye** el soporte Linux (llegó después).
- **v0.2.0 a medias: BORRADOR de release en GitHub con el paquete Linux; el `.exe` ya está compilado y probado en Windows (2026-11-22) pero falta subirlo y publicar desde Fedora.** Ver §8.1.

### 8.1 Terminar la release v0.2.0 (pendiente: subir el `.exe` y publicar desde Fedora)
Hecho en Fedora el 2026-11-21 y rehecho el 2026-11-22:
- Etiqueta anotada `v0.2.0` en el commit `c7a3c77` (subida a GitHub). El 2026-11-22 se movió desde `5579713` para incluir la prueba de protocolos de línea K del ELM327 (§7.4); el borrador nunca fue público. Los commits posteriores solo tocan documentación.
- Paquete Linux `ToledoDiagnosis-v0.2.0-linux-x86_64.tar.gz` (40 150 204 bytes) generado con `./linux/build-portable.sh v0.2.0` desde ese commit (lleva el código de línea K, comprobado dentro del binario); pasó la autoprueba IA, `tests/prueba_simuladores.py` y `tests/prueba_gui.py`. Ya trae el apartado Bluetooth en `LEEME.txt`.
- Release **en borrador** (`--draft --prerelease`, título «v0.2.0 — Linux») con ese `.tar.gz` y las notas ya escritas (mencionan los dos archivos y la prueba de línea K). Un borrador no es público: la web (`web.js`, API sin autenticar) sigue ofreciendo la v0.1.0 hasta publicarla. En la web de GitHub el borrador aparece en *Releases* solo para el dueño (su URL es `.../releases/tag/untagged-…` hasta que se publica).

Hecho en Windows el 2026-11-22:
- `git pull` + `git fetch --tags --force`; `v0.2.0` → `c7a3c77` comprobado.
- `.exe` compilado con `build.bat` **desde la etiqueta `v0.2.0`**: `C:\Users\jose\Desktop\obd2\dist\ToledoDiagnosis.exe`, **27 532 584 bytes**, SHA-256 `86FCCCD3B758F5BED56D9E430C82158DFD149BB47D5DB6AFDA3253CD74A98C56`. (`dist/` no está en git: el archivo solo existe en el disco de Windows.)
- Probado: `tests\prueba_simuladores.py` → «TODO CORRECTO» (con las 3 pruebas de línea K); `--autotest-ia` → los 3 proveedores «API key … no válida», ningún «FALLO»; el usuario abrió el `.exe` y probó el Simulador en KKL y ELM327 (bien).
- **No se subió**: en Windows no está instalado `gh`.

**Pendiente, a hacer desde Fedora** (donde `gh` tiene sesión):
1. Conseguir el `.exe` del disco de Windows. Desde Fedora se puede montar la partición NTFS (Archivos → disco de Windows, o `udisksctl mount -b /dev/<partición>`); queda en una ruta tipo `/run/media/$USER/<etiqueta>/Users/jose/Desktop/obd2/dist/ToledoDiagnosis.exe`. Copiarlo a una carpeta temporal y comprobar el tamaño y `sha256sum` de arriba. Si NTFS no monta (Windows hibernado/«inicio rápido»), apagar Windows del todo (`shutdown /s /t 0`) o que el usuario lo suba en la web (GitHub → *Releases* → borrador v0.2.0 → *Edit* → arrastrar el `.exe` → *Update release*).
2. Subirlo con el nombre `ToledoDiagnosis.exe` (el mismo que en la v0.1.0): `gh release upload v0.2.0 /ruta/ToledoDiagnosis.exe`.
3. Pedir confirmación al usuario y publicar (sigue como pre-release): `gh release edit v0.2.0 --draft=false`.
4. Comprobar: `gh release view v0.2.0` (dos archivos: `.exe` y `linux-x86_64.tar.gz`) y que los botones «Descargar» de https://www.jasodev.es apuntan a la v0.2.0 (los coge solos de la API de GitHub; no hace falta volver a publicar la web).
5. Actualizar esta sección, §8, §10 y el «Estado» de `CLAUDE.md` (release v0.2.0 publicada con `.exe` y paquete Linux) y hacer commit + push.

Si hubiera que rehacer el paquete Linux, se hace en Fedora con `./linux/build-portable.sh v0.2.0` y `gh release upload v0.2.0 <tar.gz> --clobber`.
- Crear releases: con `gh release create vX.Y.Z <archivos> --prerelease --notes-file notas.md` (en Fedora, tras `gh auth login`) o desde la web de GitHub.
- En Windows el push lo hace el usuario (`! git -C C:/Users/jose/Desktop/obd2 push`, barras normales porque `!` usa bash) porque el login de GitHub es interactivo.

---

## 9. Estado actual y limitaciones (ser honesto en la web)
- **Probado**: todo contra los simuladores; IA contra la API real (Claude) con el simulador; ejecutable de Windows; en Linux, el código y la GUI en Fedora 44 y el paquete portable en contenedores de Ubuntu 20.04/24.04, Debian 12, Fedora 40/44, Arch y openSUSE Leap 15.6 (instala, autoprueba IA y abre la ventana).
- **Probado en coches reales** (un par de coches, noviembre 2026): funciona bien. La web ya no dice que esté sin probar con coche.
- **No probado todavía**: en Linux, los adaptadores físicos (FTDI, `rfcomm`) y el lanzador en un escritorio GNOME/KDE real.
- Ajustes probables al probar con coche: tiempos entre bytes (`--retardo` en consola), alguna fórmula VAG, textos de averías.
- Tabla de averías VAG pequeña (14 códigos); los demás salen con número y «no incluido en la tabla».
- La lista de fórmulas VAG viene de documentación pública del protocolo; si una fórmula no se conoce se muestra `a=.. b=..`.
- No hay funciones de adaptación, ajustes básicos, codificación ni test de actuadores (solo lectura y borrado de averías).

## 10. Ideas pendientes / hoja de ruta
- Terminar la release v0.2.0: borrador con el paquete Linux; `.exe` compilado y probado en Windows, falta subirlo desde Fedora y publicarla (§8.1).
- Ampliar averías VAG y descripciones; más grupos documentados.
- Test de actuadores / ajustes básicos KW1281 (con mucho cuidado).
- Adaptador inalámbrico propio con ESP32 haciendo KW1281.
- Firma del ejecutable de Windows (evitar SmartScreen).

## 11. Comprobación en Linux
Hecha el 2026-11-21 en Fedora 44 (Python 3.14, Tk 9.0, Wayland): pruebas de protocolo y de GUI, `build.sh`, `build-portable.sh` y el paquete en contenedores (§9). Para repetirla en un equipo nuevo:

1. `sudo dnf install python3 python3-tkinter git`
2. `git clone https://github.com/jaso69/obd2.git && cd obd2`
3. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
4. `.venv/bin/python tests/prueba_simuladores.py` → debe decir «TODO CORRECTO».
5. `.venv/bin/python gui.py` → revisar fuentes, icono, colores, simulador en ambos modos, pestaña IA (introducir la clave: en Linux hay que volver a ponerla).
6. `xvfb-run -a .venv/bin/python tests/prueba_gui.py` → «TODO CORRECTO».
7. `./linux/build-portable.sh` (hace la autoprueba de IA) y probar el `.tar.gz`: `./instalar.sh` y abrir desde el menú.

---

## 12. Guion para la web

**Estado (2026-11-21): publicada en https://www.jasodev.es** (código en `web/` de este repositorio):
- `web/index.html` (una sola página con las secciones de §12.2), `web/estilo.css` (colores de §7.5, fuentes del sistema, sin recursos de terceros), `web/web.js` (menú móvil, selector KKL/OBD2 de capturas, visor ampliado y enlaces de descarga).
- Descargas: `web.js` consulta `api.github.com/repos/jaso69/obd2/releases` (incluye pre-releases, que `releases/latest` ignora) y apunta los botones al `.exe` y al `*linux*.tar.gz` de la última release; sin JS o sin paquete, llevan a la página de releases.
- Capturas: `xvfb-run -a -s "-screen 0 2400x1500x24 -dpi 144" python3 web/capturas.py` → `web/img/*.webp` + `og.jpg` (1200×630 para redes). Usa los simuladores en una pantalla virtual; en la conversación de IA solo se sustituye la llamada al modelo por un guion (herramientas reales, texto de ejemplo coherente con los datos del simulador; la web lo aclara). Regenerar si cambia la interfaz.
- Ver en local: `python3 -m http.server -d web 8000` → http://127.0.0.1:8000
- Publicación: `./web/publicar.sh ["mensaje"]` sustituye el contenido del repositorio https://github.com/jaso69/jasodev (enlazado con Vercel, dominio `www.jasodev.es`; `jasodev.es` redirige con 301) por `web/` (sin `capturas.py` ni `publicar.sh`) y lo sube con un commit normal; Vercel la publica en segundos. La web anterior de ese repositorio (jaso-panel) quedó en su historial (commit `5d19498`).
- `web/vercel.json`: cabeceras de seguridad (CSP sin scripts ni estilos en línea; `connect-src` permite `https://api.github.com` para los botones de descarga) y caché de `img/`. Si se añade un script o estilo en línea al HTML, la CSP lo bloqueará. `robots.txt` y `sitemap.xml` apuntan a `www.jasodev.es`.


### 12.1 Público y tono
Aficionados a la mecánica y dueños de coches VAG antiguos (y de cualquier coche con
OBD2) que quieren diagnosticar en casa. Español de España, cercano y claro, técnico
pero sin jerga innecesaria. Honesto sobre el estado (versión preliminar).

### 12.2 Estructura propuesta
1. **Inicio**: titular, subtítulo, captura grande del Panel, botones «Descargar para Windows» / «Descargar para Linux» / «Ver en GitHub». Tres puntos fuertes: VAG antiguos por KKL · cualquier OBD2 con ELM327 · asistente IA que hace las comprobaciones.
2. **Características**: una sección por pestaña con captura (§2).
3. **Asistente IA**: cómo funciona el diagnóstico guiado, ejemplo de conversación, proveedores, cómo conseguir la clave, coste aproximado, privacidad, normas de seguridad (§6).
4. **Compatibilidad y hardware**: qué cable comprar y cuál evitar, cómo comprobar el chip FTDI, Bluetooth (§3).
5. **Descargas e instalación**: Windows (SmartScreen, latencia FTDI), Linux (dialout, rfcomm, instalar.sh), desde código (§4).
6. **Guía de uso**: primeros pasos, simulador, grabar CSV, grupos útiles (§4.3, §5).
7. **Preguntas frecuentes / solución de problemas** (§12.4).
8. **Aviso legal** (§12.5) y enlace al código.

### 12.3 Capturas a preparar (usar el Simulador)
- Panel KKL con lectura en marcha (relojes y gráficas de turbo/masa de aire).
- Panel ELM327.
- Valores medidos con varios grupos y grabación activa.
- Averías KKL (00553 y 01262 intermitente) y averías OBD2 (P0171, P0420, pendiente P0301, MIL).
- Pestaña Vehículo.
- Asistente IA en mitad de un diagnóstico guiado (líneas ⚙ y diálogo «Acción solicitada por la IA»).
- Icono y foto del cable KKL / ELM327 conectados al coche.

### 12.4 FAQ / problemas típicos
- *No conecta con KKL («Sin byte de sincronismo 0x55»)*: contacto quitado, puerto equivocado, cable CH340 en vez de FTDI, FTDI falso, radio no original bloqueando la línea K, posición del interruptor (cables Fiat).
- *Keywords KWP2000*: la centralita no habla KW1281 → usar ELM327.
- *Se corta la sesión*: latencia FTDI a 1 ms (Windows), retardo entre bytes.
- *ELM327: «el vehículo no responde a OBD2»*: contacto, coche sin OBD2 (VAG antes de 2004 → KKL).
- *Bluetooth*: Windows crea dos COM (probar el otro); Linux `rfcomm bind`. La web tiene un bloque «Conectar un ELM327 Bluetooth» (`#bluetooth`, en «Qué cable necesitas») que explica que al emparejar se crea un puerto serie y se elige ese puerto, paso a paso en Windows y Linux.
- *Linux «Permission denied»*: grupo dialout (Arch: uucp).
- *Linux: el cable no aparece como /dev/ttyUSB0 (Ubuntu/Mint)*: quitar brltty.
- *IA «API key no válida» / «sin saldo»*: revisar clave y facturación del proveedor; *«modelo no encontrado»*: cambiar el nombre del modelo.
- *SmartScreen*: ejecutable no firmado.

### 12.5 Aviso legal (texto base)
«Toledo Diagnosis es software libre bajo licencia MIT y un proyecto independiente, sin relación con SEAT, Volkswagen
Group, Bosch, FTDI, Elm Electronics, Anthropic, OpenAI ni DeepSeek. Las marcas
pertenecen a sus propietarios. El programa se ofrece tal cual, sin garantía; úsalo
bajo tu responsabilidad. No realices pruebas que distraigan de la conducción. Las
sugerencias del asistente de IA son orientativas y no sustituyen a un taller.»

### 12.6 Palabras clave (SEO)
diagnosis OBD2 portátil, KW1281, cable KKL 409.1, VAG-COM, EDC15, SEAT Toledo TDI,
1.9 TDI averías, ELM327 Bluetooth, lector OBD2 gratis, diagnóstico con IA, Linux OBD2.

---

## 13. Notas para trabajar con Claude en este proyecto
- Idioma: español. El usuario desarrolla en Windows; la web la hará en Fedora.
- No hacer capturas de pantalla del escritorio mientras el usuario trabaja (se capturó su navegador una vez). Para revisar la interfaz sin molestar no sirve una ventana fuera de pantalla (sale en blanco).
- Tk Text: borrar con `delete(marca, "end-1c")`, no `"end"` (se come un salto de línea).
- Consultas reales a la API de IA gastan saldo del usuario: pedir permiso antes.
- Las claves nunca van al repositorio (están en `%APPDATA%` / `~/.config`).
