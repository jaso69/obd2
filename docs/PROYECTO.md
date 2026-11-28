# OBD2Desk — Documentación completa del proyecto

Documento de referencia para (1) crear la web del programa y (2) retomar el
desarrollo en cualquier equipo sin tener que volver a explicar el proyecto.
Última actualización: 2026-11-27 (código en `main`: renombrado a OBD2Desk y con inglés, sin publicar todavía; la última release es la v0.3.0, aún con el nombre Toledo Diagnosis).

- Repositorio: https://github.com/jaso69/obd2 (rama `main`)
- Autor: jaso69
- Licencia: **MIT** (archivo `LICENSE`, © 2026 jaso69). Permite usar, copiar, modificar y redistribuir, también comercialmente, manteniendo el aviso de copyright; sin garantía.

---

## 1. Qué es

**OBD2Desk** (hasta la v0.3.0 se llamaba *Toledo Diagnosis*) es un programa de
escritorio (Windows y Linux), en **español e inglés**, para diagnosticar coches desde un portátil:

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
**Módulo** (solo KKL: 21 direcciones VAG, entre ellas 01 motor, 02 cambio, 03 ABS, 08 clima,
15 airbag, 17 cuadro, 19 gateway, 25 inmovilizador, 35 cierre, 46 confort y 56 radio) y botón **Conectar/Desconectar**. Indicador de estado.

| Pestaña (en este orden) | Modo KKL (VAG KW1281) | Modo ELM327 (OBD2) |
|---|---|---|
| **Panel** | **Gasolina** (selector Motor): grupos 002 · 003 · 004 → relojes rpm, carga, refrigerante, temp. aire; tarjetas inyección, masa de aire, mariposa, avance, tensión; gráficas rpm y carga/mariposa. **TDI**: relojes: rpm, caudal inyectado (mg/H), presión turbo (con marca de presión teórica), refrigerante. Tarjetas: ciclo N75, ciclo EGR, tensión dosificador, masa de aire. Gráficas 60 s: turbo teórico/real (G011) y masa de aire teórica/real (G003). | Relojes: rpm, velocidad, refrigerante, carga. Tarjetas: temp. admisión, MAF, mariposa, tensión. Gráficas: rpm y carga/mariposa. |
| **Valores medidos** | Selector **Motor** (TDI bomba rotativa EDC15V / TDI inyector-bomba / gasolina con los grupos estándar de VAG): cambia las casillas de grupos habituales y el nombre de los campos; se elige solo al conectar al módulo 01 según la identificación (`detectar_motor`: EDC + referencia 038906019/012 o 03G906 → inyector-bomba; EDC → bomba rotativa; «1.8L R4/5VT»… sin EDC → gasolina). Campo para otros grupos. Tabla en vivo. Botón **Grabar CSV**. | Lista con solo los PIDs que el coche soporta (selección múltiple). Tabla en vivo. Grabar CSV. |
| (las dos) | **Gráfica en vivo** debajo de la tabla de las filas elegidas (clic; Ctrl+clic hasta 4, con colores y unidades). Guarda el último minuto de todos los valores, así que al elegir una fila sale su historia. Admite negativos. **Abrir CSV...** abre el **visor de CSV** (ventana aparte, `VisorCSV`): columnas a elegir (hasta 4), gráfica de toda la grabación (`GraficaFija`) con los valores bajo el ratón, zoom arrastrando (doble clic / clic derecho / «Ver todo» para volver) y mínimo/media/máximo del tramo visible. Lee los CSV del programa y de otros (`,` `;` o tabulador; sin columna de tiempo usa el nº de muestra). | |
| **Averías** | Códigos VAG de 5 cifras, componente, tipo de fallo, intermitente. Leer / Borrar (con confirmación). **Escanear todos los módulos**: prueba las 21 direcciones de `MODULOS` una a una (los ausentes se descartan en ~4 s), lista identificación y averías de cada módulo que responde y vuelve al módulo elegido; se puede detener. **Generar informe**. | Códigos P0xxx memorizados, pendientes y **permanentes** (modo 0A; no se borran) con descripción, estado del testigo MIL. A la derecha, **datos congelados** (modo 02) de la avería que encendió el testigo. Leer / Borrar. **Generar informe**. |
| (Averías, las dos) | **Historial por coche**: cada lectura, borrado y escaneo se guarda solo en `historial/<id>.json` de la carpeta de configuración (la misma lectura antes de 30 min no se duplica). Coche = VIN; si no hay, en OBD2 la calibración (`CALID-…`) y en VAG el VIN si sale en la identificación o la referencia de la centralita de motor (`VAG-038906018FQ`; el escaneo la descubre aunque se conecte a otro módulo). Debajo de los botones, comparación con el diagnóstico anterior de los mismos módulos: nuevas, ya no aparecen, se repiten (también va al contexto de la IA). **Historial...** abre `VentanaHistorial`: elegir coche, lista de diagnósticos, detalle con su comparación y borrar un diagnóstico. | |
| **Vehículo** | Identificación de la centralita (referencia, componente, software, codificación), velocidad, keywords, eco del cable. | Adaptador, protocolo, VIN **decodificado** (fabricante, país, año modelo, modelo VAG), tensión de batería, estándar OBD, MIL, nombre de la centralita, calibración (CALID) y CVN (modo 09), nº de PIDs. A la derecha, **monitores de preparación** (readiness, para la ITV). |
| **Consumo y 0-100** | **Gasolina** (selector Motor): grupos 002 (masa de aire g/s, o presión del colector con la **Cilindrada**) y 005 (velocidad) → L/100 km, distancia y 0-100 como en OBD2. **TDI**: consumo con el caudal inyectado del grupo 001 × régimen × cilindros (campo **Cilindros**, por defecto 4): L/h, litros gastados, tiempo y gráfica. La EDC15 no da la velocidad: sin L/100 km ni 0-100 (se explica en la pestaña). | Consumo instantáneo (L/100 km, o L/h parado), medio, litros, distancia y tiempo del trayecto (**Reiniciar trayecto**) y gráfica. Cálculo: PID 5E si existe; si no, aire (MAF, o estimado con MAP + rpm + temp. admisión + **Cilindrada**) / (14,7 o 14,5 × lambda). Lambda: gasolina la comandada (PID 44) o 1; diésel necesita la sonda de banda ancha (PID 24/34), si no, no se calcula. **Combustible** gasolina/diésel (se detecta con el PID 51 si el coche lo da). **Cronómetro 0-100** con paso por 50: se arma con el coche parado, arranca solo, interpola los cruces entre muestras; se anula si baja la velocidad >5 km/h, si para o si hay un hueco de lecturas; últimas 5 medidas y mejor. Solo lee los PIDs necesarios (más muestras/s). Ajustes guardados en la configuración (`consumo`). |
| **✦ Asistente IA** | Igual en ambos modos (ver §6). | |
| **Registro** | Historial de la comunicación; opción de depuración que muestra cada bloque/comando. | |
| **Ayuda** | Manual de uso (`ayuda.py`, `secciones()`): índice de apartados a la izquierda (clic → salta al apartado) y texto a la derecha, en el orden de las pestañas. Traducido en `textos_en.py`. | |

Otros detalles:
- **Puerto**: en OBD2 la lista incluye «WiFi · 192.168.0.10:35000» y el campo se puede escribir (otra dirección `ip:puerto` de un ELM327 WiFi). Se abre con `serial.serial_for_url("socket://ip:puerto")`.
- **Informe** (`informe.py`): HTML de un solo archivo `informe_AAAAMMDD_HHMMSS.html` en la misma carpeta que los CSV; se abre en el navegador, con botón «Imprimir o guardar como PDF». Lleva datos del vehículo, averías (y el último escaneo de módulos en KKL) y, en OBD2, datos congelados y monitores.
- **Aviso de versión nueva**: al arrancar, un hilo consulta `api.github.com/repos/jaso69/obd2/releases/latest` (5 s como mucho; sin datos del usuario, User-Agent `OBD2Desk`) y, si la etiqueta es mayor que `VERSION` de `gui.py`, muestra «↑ Nueva vX.Y.Z» junto al título (clic → página de la release). La variable de entorno `OBD2DESK_SIN_COMPROBAR_VERSION=1` lo desactiva (la usan las pruebas).
- **Idioma**: selector «Español / English» junto al nombre del programa. Por defecto, el del sistema (`idioma.detectar()`: español si el sistema está en español, catalán, gallego o euskera; si no, inglés); la elección se guarda en `config.json` (`"idioma"`). Al cambiarlo se desconecta si hace falta y la ventana se reconstruye sin cerrar el programa. El asistente IA usa el prompt del idioma elegido. Ver §7.6. **Al publicar una versión hay que subir `VERSION` en `gui.py`.**
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
- **Ejecutable**: `OBD2Desk.exe` (≈26 MB, un solo archivo; hasta la v0.3.0, `ToledoDiagnosis.exe`). Se genera con `build.bat` en `dist\`. No necesita Python.
- SmartScreen avisará la primera vez (no está firmado): «Más información → Ejecutar de todas formas».
- Cable FTDI: el driver lo instala Windows Update (si no, driver VCP de FTDI). **Poner la latencia a 1 ms**: Administrador de dispositivos → Puertos → USB Serial Port → Propiedades → Configuración de puerto → Opciones avanzadas → Temporizador de latencia = 1. Es por equipo: repetir en cada PC.
- Desde código: `pip install -r requirements.txt` y `python gui.py` (o doble clic en `OBD2Desk.pyw`).

### 4.2 Linux (comprobado en Fedora 44 y en contenedores de 7 distros, ver §11)
- Requisitos para ejecutar desde código: Python 3.10+ y tkinter.
  - Fedora: `sudo dnf install python3 python3-tkinter`
  - Debian/Ubuntu: `sudo apt install python3 python3-venv python3-tk`
  - Luego: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python gui.py`
- **Ejecutable local**: `./build.sh` genera `dist/OBD2Desk` (binario único con PyInstaller, usa un venv `.venv`). Solo vale para distros con una glibc igual o más nueva que la del equipo donde se compila (compilado en Fedora 44 no arranca en Ubuntu 22.04).
- **Para distribuir**: `./linux/build-portable.sh [versión]` compila dentro de un contenedor Debian 11 (podman o docker, imagen `python:3.13-bullseye`, glibc 2.31), pasa la autoprueba de IA y genera `dist/OBD2Desk-<versión>-linux-x86_64.tar.gz` (carpeta `OBD2Desk/`) con: `OBD2Desk`, `instalar.sh`, `obd2desk.desktop`, `icono.png`, `LEEME.txt` y `README.txt` (`linux/`, español e inglés) y `LICENSE`. Funciona en Ubuntu 20.04+, Debian 11+, Mint 20+, Fedora, openSUSE, Arch.
- **Instalar en el menú**: `./instalar.sh [ejecutable]` (desde el paquete) o `./linux/instalar.sh` (desde el repositorio) → copia a `~/.local/bin/OBD2Desk`, icono y lanzador `obd2desk.desktop` (sin sudo); si encuentra la instalación anterior (`ToledoDiagnosis`, `toledo-diagnosis.desktop`) la quita. `--desinstalar` (o `--uninstall`) lo quita (deja la configuración). Mensajes en español o inglés según `LANG`.
- **Permisos del puerto serie**: `sudo usermod -aG dialout $USER` (en Arch el grupo es `uucp`) y cerrar sesión. Sin esto sale «Permission denied»; el programa y el instalador detectan el grupo del puerto y dicen el comando exacto.
- **brltty** (Ubuntu/Mint): el lector braille captura adaptadores USB-serie (CH340, a veces FTDI) y `/dev/ttyUSB0` desaparece. Solución: `sudo apt remove brltty`. El instalador avisa si está.
- **Lanzador**: Tk pone la clase de ventana `Obd2desk` (capitaliza `className="OBD2Desk"` y pasa el resto a minúsculas; comprobado con `xprop`), por eso `StartupWMClass=Obd2desk` en el `.desktop`; si no coincide, el dock muestra un icono genérico duplicado.
- **CSV e informes**: con el binario van a `Documentos/OBD2Desk` (`xdg-user-dir DOCUMENTS`); desde el código, junto a `gui.py`. En Windows, junto al `.exe`.
- Puertos: cable FTDI = `/dev/ttyUSB0`; ELM327 USB = `/dev/ttyUSB0` o `/dev/ttyACM0`; ELM327 Bluetooth: `bluetoothctl` (pair, trust) y `sudo rfcomm bind 0 AA:BB:CC:DD:EE:FF` → `/dev/rfcomm0`.
- Latencia FTDI: en Linux el programa activa el modo de baja latencia automáticamente (`set_low_latency_mode`), equivalente a poner 1 ms.
- Clave de IA en `~/.config/OBD2Desk/config.json` (Windows: `%APPDATA%\OBD2Desk`) con permisos 600; si no existe y sí la de la versión anterior (`ToledoDiagnosis/config.json`), `ia._ruta_config()` la copia la primera vez (no cifrada; en Windows va cifrada con DPAPI).
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

Desde el 2026-11-28 hay también tablas para el **TDI inyector-bomba** (`GRUPOS_PD`, del
«Display group overview» del manual de taller: 001, 002, 003, 004 con comienzo/tiempo de
inyección y ángulo de sincronización, 006 pedales, 007, 008 con limitación por humos, 010, 011,
013, 018 estado de los inyectores-bomba, 023 tiempo de conmutación) y para **gasolina**
(`GRUPOS_GASOLINA`, grupos estándar de Ross-Tech para motores de 1999-2000 en adelante: 001-005,
010, 011, 020/022/023 picado, 031-033 lambda, 115 y 118 turbo). En gasolina algunos grupos
cambian según el motor (caudalímetro o sensor de presión, 1 o 2 bancos): el nombre del campo lo
indica entre paréntesis. Se eligen con el selector **Motor** de Valores medidos (ver §2).

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
  - `grabar_valores` — graba 2-120 s (como mucho 50 muestras/s) a `ia_AAAAMMDD_HHMMSS.csv` en la carpeta de documentos (se abre en el visor de CSV) y devuelve mín/media/máx de cada valor y ~25 muestras de la serie.
  - `consultar_historial` — diagnósticos guardados del coche conectado (o de otro con `coche`) con nuevas/ya no aparecen/se repiten frente al anterior; sin coche, lista los coches guardados.
  - `generar_informe` — lee las averías y genera el informe HTML con la sección «Diagnóstico del asistente IA» (Markdown sencillo convertido y escapado en `informe._markdown`) y lo abre en el navegador.
- Todos los informes (también los manuales) llevan la comparación con el diagnóstico anterior si el coche está identificado.
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
| `consumo.py` | Cálculo de consumo (`litros_hora_obd`, `litros_hora_vag`, `metodo`, `pids_necesarios`), `Trayecto` (integra litros y km; no suma tramos con huecos >3 s; instantáneo = media de 2 s) y `Cronometro` (0-100 con paso por 50). Sin interfaz. |
| `csv_datos.py` | Lectura de CSV para el visor (`leer`: separador y coma decimal automáticos, «nombre (unidad)»), `resumen` (mín/media/máx de un tramo) y `reducir` (mín/máx por tramo para dibujar miles de puntos sin perder picos). |
| `ayuda.py` | Textos del manual de la pestaña «Ayuda» (`secciones()` → `[(título, [párrafos])]`; un párrafo que empieza por «• » es un punto de lista). Al cambiar una función, actualizar aquí su explicación. |
| `cambios.py` | Registro de los cambios escritos en las centralitas VAG (adaptación y codificación) con el valor de antes (`cambios_centralita.jsonl`). Sin interfaz. |
| `historial.py` | Historial por coche (`Historial`: `guardar` con fusión de lecturas repetidas, `cargar`, `coches`, `borrar_registro`), `comparar` (solo módulos comunes), `anterior`, `buscar_vin`. Sin interfaz. |
| `kw1281.py` | Protocolo KW1281: init 5 baudios por *break*, detección de velocidad, eco, complementos, bloques, keep-alive en hilo, averías, borrado, grupos. |
| `informe.py` | Informe de diagnóstico HTML (escapa todo el texto; CSS de impresión). |
| `vin_datos.py` | Decodificación del VIN: tabla WMI de fabricantes, país, año modelo (posición 10, ciclo de 30 años), código de modelo VAG (posiciones 7-8). |
| `vag_datos.py` | Fórmulas de valores medidos VAG (≈60), tipos de fallo, averías VAG de 5 cifras (≈90 clásicos 00xxx-01xxx, los P1 de `vag_p1.py` y traducción de 16xxx-18xxx a P0/P1), grupos por motor (`GRUPOS_EDC15`, `GRUPOS_PD`, `GRUPOS_GASOLINA`, `MOTORES`, `detectar_motor`), 21 módulos. |
| `vag_p1.py` | 538 averías P1 de VAG (17xxx-18xxx) en español e inglés: `P1[código] = (es, en)`. Fuente: tabla de Bentley Publishers (pics.tdiclub.com/data/500/7938dtc.pdf), solo filas con número VAG. No pasan por `textos_en.py`. En OBD2 se usan si el VIN es de VAG (`obd_datos.marca_vag`). |
| `elm327.py` | OBD2 por ELM327: inicialización, protocolo automático, parseo con cabeceras (CAN 11/29 bits y línea K), reensamblado ISO-TP, multi-PID, averías (03/07/0A/04), datos congelados (02), monitores (01 01), VIN y CALID/CVN/nombre (09 02/04/06/0A), MIL, tensión. |
| `obd_datos.py` | PIDs del modo 01 (≈50) con decodificadores, estándares OBD, descripciones de averías P0xxx (≈110, revisadas a mano, tienen prioridad), monitores de preparación (gasolina y diésel). `describe_dtc`: revisadas → P1 de VAG (si `marca_vag`) → tabla genérica `obd_codigos.py` → «específico del fabricante». |
| `obd_codigos.py` | **Generado** por `herramientas/codigos_genericos.py`: 9533 códigos genéricos SAE J2012 (P0, P2, P3, B0, C0, U0, U3) → (inglés, español o None). Inglés de OBDex (CC0, `herramientas/obdex_titulos.json`, commit 9ba1ffa); español con `herramientas/traductor_dtc.py` (diccionario de nombres con género y artículo, adjetivos, fallos y plantillas; recompone «Exhaust Gas Temperature Sensor» → «Sensor de temperatura de los gases de escape»). 94,6 % traducido; el resto se muestra en inglés. Prueba: `tests/prueba_codigos.py`. |
| `ia.py` | Proveedores, configuración y claves (y migración desde `ToledoDiagnosis`), `Conversacion` (bucle de herramientas para Anthropic y OpenAI/DeepSeek), prompt de sistema en español e inglés, definición de herramientas (`herramientas()` las da traducidas). |
| `idioma.py` | Idioma de la interfaz: `tr()`, `poner()`, `detectar()`, registro de tablas de datos que se traducen en su sitio (`tabla()`). |
| `textos_en.py` | Diccionario español → inglés de todos los textos (≈790). |
| `simulador.py` | `FakeSerial` (cable KKL + centralitas a 9600 bd: motor EDC15 01, ABS 03, airbag 15 y cuadro 17; decodifica el init de 5 baudios por tiempos reales) y `FakeELMSerial` (ELM327 + coche gasolina CAN 11/500 o línea K, PID 51 = gasolina, velocidad 0 → 130 km/h en ciclos de 25 s para el 0-100, con datos congelados de la P0171, permanente P0420, EVAP sin completar y CALID/CVN). |
| `toledo.py` | Versión consola KKL (y utilidades reutilizadas por la GUI: `leer_grupo_formateado`, `texto_id`). |
| `sonda_toledo.py` | Sonda de protocolos con ELM327 para el Toledo. |
| `tests/prueba_simuladores.py` | ≈60 comprobaciones contra los simuladores (`python tests/prueba_simuladores.py`, ≈20 s): KW1281 (también varias centralitas), ELM327 en CAN y línea K (datos congelados, monitores, permanentes, modo 09), VIN, informe y tablas de averías. |
| `tests/prueba_consumo.py` | Cálculo del consumo (PID 5E, MAF, MAP, diésel con/sin lambda, EDC15), trayecto y cronómetro 0-100 con casos de resultado conocido (<1 s). |
| `tests/prueba_csv.py` | Lector de CSV (del programa y de otros, errores, reducir puntos) (<1 s). |
| `tests/prueba_historial.py` | Historial: guardar, no duplicar, comparar (también escaneo frente a lectura de un módulo), varios coches, archivos dañados, VIN en la identificación VAG; registro de cambios de adaptación/codificación (<1 s). |
| `tests/prueba_idioma.py` | Comprueba (≈1 s) que todo `tr("...")` del código y todas las tablas tienen traducción, que coinciden los huecos `{nombre}`, que no hay claves repetidas ni español en las traducciones. |
| `tests/prueba_gui.py` | Maneja la ventana real con los dos simuladores: conectar, averías, escaneo de módulos, datos congelados, monitores, informe, panel, consumo y 0-100 (en ELM327 adelanta el reloj del simulador para medir un 0-100 de 3,3 s), valores + CSV + gráfica en vivo de filas elegidas + visor del CSV grabado (ratón, zoom, resumen), historial (coche identificado, primera lectura, comparación tras borrar, ventana con los registros), herramientas de la IA llamadas como lo haría el modelo sin API (`leer_valores`, `consultar_historial`, `grabar_valores`, `generar_informe`), ELM327 WiFi (servidor TCP local), configuración IA y cambio de idioma con el selector (`xvfb-run -a .venv/bin/python tests/prueba_gui.py` en Linux, ≈90 s; con `OBD2DESK_IDIOMA=en` corre en inglés y además busca restos de español en todos los textos de la ventana y en el informe). Necesita `pyserial` (el Python del sistema en Fedora no lo trae: usar `.venv`). |
| `build.bat` / `build.sh` | Ejecutable único con PyInstaller (Windows / Linux). |
| `linux/build-portable.sh` | Binario Linux portable (contenedor Debian 11) y paquete `.tar.gz` para distribuir. |
| `linux/instalar.sh`, `linux/obd2desk.desktop`, `linux/LEEME.txt`, `linux/README.txt` | Instalación de usuario en Linux y LÉEME del paquete (español e inglés). |
| `crear_icono.py` | Genera `icono.ico`/`icono.png` con Pillow (solo desarrollo). |
| `OBD2Desk.pyw` | Lanzador sin consola en Windows. |

### 7.2 Hilos
- **Hilo principal (Tk)**: interfaz. Sondea una cola cada 50 ms (`App.poll`).
- **Worker**: único hilo que habla con el puerto serie. Recibe tareas (`connect`, `disconnect`, `dtcs`, `clear`, `scan`, `report`, `live`, `debug`, `tool`) y publica eventos (`connected`, `live`, `dtcs`, `scan_progress`, `scan_done`, `report`, `lost`, `error`, `log`…). Durante el escaneo pone `online = False` para que el cambio de módulo no cuente como conexión perdida; `scan_stop` (Event) lo detiene desde la interfaz. Las lecturas en vivo llevan un número de generación para descartar datos de lecturas anteriores.
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
- Datos congelados: `020200` da el código que los provocó (0000 = no hay); `020000` (y 0220…) los PIDs disponibles; luego `02PP00` uno a uno. Monitores: bytes B/C/D de `0101` (bit 3 de B = diésel). Modo 09: CALID 16 bytes, CVN 4 bytes, nombre 20 bytes; en línea K llegan en mensajes de 4 bytes numerados y se concatenan.

### 7.5 Estilo visual (para la web)
- Tema oscuro. Colores: fondo `#111418`, panel `#181c22`, tarjeta `#1f242c`, tarjeta 2 `#262c36`, pista `#2f3642`, texto `#e8ebf0`, texto secundario `#8a93a2`, **acento naranja `#ff7a29`**, azul `#4aa8ff`, ok `#3ccf7a`, aviso `#f5b83d`, error `#ef5350`.
- Fuentes: Segoe UI (Windows), Noto Sans (Linux).
- Icono: reloj de turbo naranja con aguja y texto «TDI» sobre cuadrado oscuro redondeado (`icono.png` 256 px, `icono.ico` multi-tamaño).

### 7.6 Idioma (español e inglés)
- Los textos se escriben **en español en el código** envueltos en `tr()` (`from idioma import tr`); con datos variables, `tr("Conectado a {baud} baudios", baud=x)` (nada de f-strings dentro de `tr`). En inglés, `tr()` busca el texto en `textos_en.EN`; si falta, deja el español y lo apunta en `idioma.faltan`.
- Tablas de datos (averías VAG y OBD2, tipos de fallo, módulos, grupos EDC15, PIDs, estándares OBD): se registran con `idioma.tabla(dict[, fn])` y `idioma.poner()` las traduce en su sitio conservando el original. Monitores, países del VIN y textos entre paréntesis de fabricantes/modelos se traducen al usarse.
- Textos que hacen de valor (puerto «Simulador (sin coche)», modos de conexión) se recalculan en `gui._textos_fijos()` al crear la ventana.
- **Al añadir o cambiar un texto: añadirlo a `textos_en.py` y pasar `python tests/prueba_idioma.py`** (dice qué falta). La prueba de GUI en inglés detecta textos visibles sin `tr()`.
- `OBD2DESK_IDIOMA=es|en` fuerza el idioma (pruebas y capturas) por encima de la configuración.
- `toledo.py` (consola) y `sonda_toledo.py` siguen solo en español; los mensajes de depuración (`[elm327] …`) tampoco se traducen.

---

## 8. Compilar, versionar y publicar
- Windows: `build.bat` → `dist\OBD2Desk.exe`. Linux: `./build.sh` → `dist/OBD2Desk` (uso local); para publicar, `./linux/build-portable.sh vX.Y.Z` → `dist/OBD2Desk-vX.Y.Z-linux-x86_64.tar.gz`. (Hasta la v0.3.0 los archivos se llamaban `ToledoDiagnosis…`.)
- Tras cambiar código, recompilar y copiar el ejecutable nuevo.
- Comprobación rápida del ejecutable (sin gastar saldo): `OBD2Desk --autotest-ia salida.txt` → debe poner «API key … no válida» para los 3 proveedores (confirma que los SDK y HTTPS funcionan dentro del binario).
- Git: etiqueta `v0.1.0` en el commit inicial `a354d67`. **Release v0.1.0 publicada** (marca de pre-release quitada el 2026-11-22) con `ToledoDiagnosis.exe` de Windows compilado desde esa etiqueta: https://github.com/jaso69/obd2/releases/tag/v0.1.0 — descarga directa: https://github.com/jaso69/obd2/releases/download/v0.1.0/ToledoDiagnosis.exe
- La v0.1.0 **no incluye** el soporte Linux (llegó después).
- **Release v0.3.0 publicada** (2026-11-22, «Latest») con `ToledoDiagnosis.exe` de Windows y el paquete Linux, ambos compilados desde la etiqueta `v0.3.0` (`5c83aa6`): https://github.com/jaso69/obd2/releases/tag/v0.3.0 — la web ofrece ya esta versión en los dos sistemas. Detalle en §8.2.
- **Release v0.2.0 publicada** (2026-11-22) con `ToledoDiagnosis.exe` de Windows y `ToledoDiagnosis-v0.2.0-linux-x86_64.tar.gz`, ambos compilados desde la etiqueta `v0.2.0` (`c7a3c77`): https://github.com/jaso69/obd2/releases/tag/v0.2.0 — la web ofrece ya esta versión. Detalle en §8.1.

### 8.1 Release v0.2.0 (publicada el 2026-11-22)
Hecho en Fedora el 2026-11-21 y rehecho el 2026-11-22:
- Etiqueta anotada `v0.2.0` en el commit `c7a3c77` (subida a GitHub). El 2026-11-22 se movió desde `5579713` para incluir la prueba de protocolos de línea K del ELM327 (§7.4); el borrador nunca fue público. Los commits posteriores solo tocan documentación.
- Paquete Linux `ToledoDiagnosis-v0.2.0-linux-x86_64.tar.gz` (40 150 204 bytes) generado con `./linux/build-portable.sh v0.2.0` desde ese commit (lleva el código de línea K, comprobado dentro del binario); pasó la autoprueba IA, `tests/prueba_simuladores.py` y `tests/prueba_gui.py`. Ya trae el apartado Bluetooth en `LEEME.txt`.
- Release **en borrador** (`--draft --prerelease`, título «v0.2.0 — Linux», cambiado a «Toledo Diagnosis v0.2.0» al publicarla) con ese `.tar.gz` y las notas ya escritas (mencionan los dos archivos y la prueba de línea K). Un borrador no es público: la web (`web.js`, API sin autenticar) sigue ofreciendo la v0.1.0 hasta publicarla. En la web de GitHub el borrador aparece en *Releases* solo para el dueño (su URL es `.../releases/tag/untagged-…` hasta que se publica).

Hecho en Windows el 2026-11-22:
- `git pull` + `git fetch --tags --force`; `v0.2.0` → `c7a3c77` comprobado.
- `.exe` compilado con `build.bat` **desde la etiqueta `v0.2.0`**: `C:\Users\jose\Desktop\obd2\dist\ToledoDiagnosis.exe`, **27 532 584 bytes**, SHA-256 `86FCCCD3B758F5BED56D9E430C82158DFD149BB47D5DB6AFDA3253CD74A98C56`. (`dist/` no está en git: el archivo solo existe en el disco de Windows.)
- Probado: `tests\prueba_simuladores.py` → «TODO CORRECTO» (con las 3 pruebas de línea K); `--autotest-ia` → los 3 proveedores «API key … no válida», ningún «FALLO»; el usuario abrió el `.exe` y probó el Simulador en KKL y ELM327 (bien).
- **No se subió**: en Windows no está instalado `gh`.

Hecho en Fedora el 2026-11-22 (cierre):
- `.exe` copiado desde la partición de Windows (montada en `/run/media/jaso/D8AE878DAE87633C/...`); tamaño y SHA-256 coinciden con los de arriba.
- Subido con `gh release upload v0.2.0 ToledoDiagnosis.exe` y publicada con `gh release edit v0.2.0 --draft=false` (como pre-release), 2026-11-22 11:24 UTC; después se le quitó la marca de pre-release con `gh release edit v0.2.0 --prerelease=false --latest` y se cambió el título.
- Comprobado: la release tiene los dos archivos; el `.exe` descargado de GitHub tiene el mismo SHA-256; la API sin autenticar que usa `web.js` (`releases?per_page=10`) devuelve `v0.2.0` primero, así que los botones «Descargar» de la web apuntan a la v0.2.0.

Si hubiera que rehacer el paquete Linux, se hace en Fedora con `./linux/build-portable.sh v0.2.0` y `gh release upload v0.2.0 <tar.gz> --clobber`.
- Crear releases: con `gh release create vX.Y.Z <archivos> --prerelease --notes-file notas.md` (en Fedora, tras `gh auth login`) o desde la web de GitHub.
- En Windows el push lo hace el usuario (`! git -C C:/Users/jose/Desktop/obd2 push`, barras normales porque `!` usa bash) porque el login de GitHub es interactivo.

---

### 8.2 Release v0.3.0 (publicada el 2026-11-22, completa)
Funciones: tabla de averías VAG ampliada, escaneo de módulos VAG, datos congelados, monitores de preparación, averías permanentes, CALID/CVN, decodificación del VIN, informe HTML, ELM327 WiFi y aviso de versión nueva (`VERSION = "0.3.0"` en `gui.py`).

Hecho en Fedora el 2026-11-22:
- Etiqueta anotada `v0.3.0` en el commit `5c83aa6` (subida).
- Paquete `ToledoDiagnosis-v0.3.0-linux-x86_64.tar.gz` (40 181 932 bytes) con `./linux/build-portable.sh v0.3.0`: autoprueba IA bien; extraído, el binario abre la ventana. Pruebas con simuladores y de la GUI en verde.
- Release **publicada** (no pre-release, «Latest»), título «Toledo Diagnosis v0.3.0», solo con el paquete Linux; las notas dicen que el `.exe` llega en breve y enlazan el de la v0.2.0. La web (`web.js`) busca el `.exe` en la release más reciente que lo tenga, así que hasta entonces el botón de Windows da el de la v0.2.0.
- Web publicada con las funciones nuevas (`./web/publicar.sh`).

Hecho en Windows el 2026-11-22:
- `git pull` + `git fetch --tags --force`; `v0.3.0^{commit}` → `5c83aa6` comprobado (`git rev-parse v0.3.0` a secas da `646e4c0`, el objeto de la etiqueta anotada).
- `.exe` compilado con `build.bat` **desde la etiqueta `v0.3.0`**: `C:\Users\jose\Desktop\obd2\dist\ToledoDiagnosis.exe`, **27 566 252 bytes**, SHA-256 `FA85A53C4E265B697BAEAAD4B1E4649987EC5048C5C346872797F9B68F983698`. (`dist/` no está en git: solo existe en el disco de Windows.)
- Probado: `tests\prueba_simuladores.py` → «TODO CORRECTO»; `--autotest-ia` → los 3 proveedores «API key … no válida»; el usuario abrió el `.exe` y probó el Simulador en KKL (escanear módulos) y ELM327 (datos congelados, Vehículo, Generar informe): bien.

Hecho en Fedora el 2026-11-22 (cierre):
- `.exe` copiado desde la partición de Windows; tamaño y SHA-256 coinciden con los de arriba. Subido con `gh release upload v0.3.0 ToledoDiagnosis.exe`; en las notas se cambió «se añadirá aquí en breve» (y el enlace a la v0.2.0) por la línea normal de descarga de Windows.
- Comprobado: la release tiene los dos archivos; el `.exe` descargado de GitHub tiene el mismo SHA-256; la API sin autenticar que usa `web.js` devuelve `v0.3.0` primero con el `.exe`, así que los botones «Descargar» de la web dan la v0.3.0.

Hecho el 2026-11-22 (después): el usuario probó la v0.3.0 en un coche y funciona bien. Web actualizada (sección «Estado del proyecto»: novedades de la v0.3.0 probadas en coche; solo queda pendiente un ELM327 WiFi real) y publicada con `./web/publicar.sh`.

**La v0.3.0 está cerrada.** Lo siguiente está en §10.

### 8.2b Release v0.4.0 (publicada y cerrada el 2026-11-27)
- Nuevo nombre **OBD2Desk** e interfaz en inglés (§7.6). Etiqueta `v0.4.0` → `c10c53f`.
- Paquete `OBD2Desk-v0.4.0-linux-x86_64.tar.gz` (40 426 446 bytes, SHA-256 `dae343ad10380c7cd401c7e8a0baf0db4bafed9d5a9e0e168aac79c72c746bee`) con `./linux/build-portable.sh v0.4.0`: autoprueba IA bien; extraído e instalado en un HOME temporal con una instalación antigua simulada: la retira, copia la configuración y abre en inglés (`WM_CLASS` `Obd2desk`). Descargado de GitHub con el mismo SHA-256.
- Release «OBD2Desk v0.4.0» publicada como «Latest» con notas en español e inglés.
- Web publicada a la vez (instrucciones de Linux con `OBD2Desk-*.tar.gz`).

Hecho en Windows el 2026-11-27: `git pull` + `git fetch --tags`, compilado desde `v0.4.0` (`c10c53f`) con Python 3.14.3 y PyInstaller 6.22.3 en Windows 10 Pro.
- `OBD2Desk.exe`: 27 607 531 bytes, SHA-256 `6ad893aa01a3c70209ccd0864bd9719bc427a3b89805ae59f73832bfbeef55f9`.
- Probado: `prueba_idioma.py`, `prueba_simuladores.py` y `prueba_gui.py` (español) → «TODO CORRECTO»; `--autotest-ia` → los 3 proveedores «API key … no válida»; migración de `%APPDATA%\ToledoDiagnosis` a `%APPDATA%\OBD2Desk` bien; el usuario abrió el `.exe` (simulador, panel, cambio de idioma): bien.
- `prueba_gui.py` en inglés daba un falso positivo en un Windows en español: la descripción del puerto real «Puerto de comunicaciones (COM1)» la pone el sistema. Arreglado en el test (quita las descripciones de `serial.tools.list_ports`); el `.exe` no cambia.

Hecho en Fedora el 2026-11-27 (cierre): `.exe` copiado de la partición de Windows con el mismo SHA-256, subido con `gh release upload v0.4.0`, quitada de las notas la frase «se subirá en breve» / «coming shortly», descargado de GitHub con el mismo SHA-256. La web ofrece ya la v0.4.0 en los dos sistemas (`web.js` toma el `.exe` de la release más reciente).

**La v0.4.0 está cerrada.**

### 8.2c Release v0.5.0 (publicada y cerrada el 2026-11-27)
- Bloque 2: consumo y 0-100, gráfica en vivo y visor de CSV, historial por coche, herramientas nuevas de la IA. **Probado en coche por el usuario** («ya está todo probado en el coche»). Etiqueta `v0.5.0` → `1c10616`.
- Pruebas antes de etiquetar: consumo, csv, historial, idioma, simuladores y GUI en español e inglés → «TODO CORRECTO».
- Paquete `OBD2Desk-v0.5.0-linux-x86_64.tar.gz` (40 512 316 bytes, SHA-256 `27a4113ac35ff6c80a4df6967f8adc3d13cf6e8c57d60663b94ea69e35fd2fde`): autoprueba IA bien; instalado en un HOME temporal y abierto (pestaña nueva presente). Descargado de GitHub con el mismo SHA-256.
- Release «OBD2Desk v0.5.0» publicada como «Latest» con notas en español e inglés; al principio decían que el `.exe` llegaba en breve (ya quitado).
- `OBD2Desk.exe` compilado en Windows 10 desde `v0.5.0` (Python 3.14.3, PyInstaller 6.22.3): 27 696 915 bytes, SHA-256 `36b79796d04b2f8e39cee1f42692b63f8883df4ae9414d0bbbd5c25780eca6eb`. Antes, todas las pruebas «TODO CORRECTO» (GUI en español e inglés); autoprueba IA: los 3 proveedores «no válida», ningún «FALLO»; el usuario probó el `.exe` con el simulador: «todo funciona bien». Subido a la release y descargado de GitHub con el mismo SHA-256; quitado «en breve» de las notas.
- `tests/prueba_csv.py` se caía en la consola de Windows (cp1252) al imprimir «→»; cambiado por «->».
- Web publicada el 2026-11-27 (`./web/publicar.sh "Web v0.5.0"`); los botones descargan la v0.5.0.

### 8.2d Release v0.6.0 y v0.6.1 (2026-11-28)
- Pestaña Ayuda (y «Consumo y 0-100» tras «Vehículo»), 538 averías P1 de VAG (también en OBD2 si el VIN es VAG), grupos de TDI inyector-bomba y de gasolina con selector de Motor, Panel y consumo/0-100 de gasolina por KKL. `VERSION = "0.6.0"`.
- Pruebas antes de etiquetar: simuladores, idioma, consumo, csv, historial y GUI en español e inglés → «TODO CORRECTO». Probado solo con simuladores: **falta probar en coche un VAG de gasolina y un TDI inyector-bomba por KKL**.
- Etiqueta `v0.6.0` → `54aa9a8`. Paquete `OBD2Desk-v0.6.0-linux-x86_64.tar.gz` (40 546 757 bytes, SHA-256 `6967a7685845941c068fbcce7e9b9d8f4bfccd02ef60588b3c4317d10abf29e5`): autoprueba IA bien; extraído, abre la ventana con la pestaña Ayuda. Descargado de GitHub con el mismo SHA-256.
- Release «OBD2Desk v0.6.0» publicada como «Latest» con notas en español e inglés; dicen que el `.exe` llega en breve (enlazan el de la v0.5.0). El `.exe` no se compila para la v0.6.0: va en la v0.6.1.
- Web: textos de la v0.6.0 y capturas rehechas (barra de pestañas con «Ayuda»).

- **v0.6.1** (2026-11-28, mismo día, antes de compilar el `.exe`): la lista de casillas de grupos de Valores medidos se desplaza con la rueda si no cabe (con los 15 grupos de gasolina el botón «Abrir CSV...» quedaba fuera de la ventana).
- Etiqueta `v0.6.1` → `bf104aa`. Paquete `OBD2Desk-v0.6.1-linux-x86_64.tar.gz` (40 550 138 bytes, SHA-256 `2154c5dd49ce283e3626d3191ef0f35bc703568d7539e26808e472c122bf6c80`): autoprueba IA bien, abre la ventana; descargado de GitHub con el mismo SHA-256. Release «OBD2Desk v0.6.1» «Latest»; las notas de la v0.6.0 remiten a la v0.6.1 para el `.exe`. Pruebas antes de etiquetar: idioma, simuladores y GUI en español e inglés → «TODO CORRECTO». `OBD2Desk.exe` compilado en Windows desde `4420a24` (mismo código que `v0.6.1`; solo cambia este documento): 27 735 666 bytes, SHA-256 `1619873a8f51204726dafc897dba1d0f521ffc69b81b496ff326ab885c48eb8d`. Copiado a Fedora con el mismo SHA-256, subido con `gh release upload v0.6.1`, quitado «en breve» de las notas y descargado de GitHub con el mismo SHA-256. El usuario abrió el `.exe` en Windows: «funciona bien». La web lo ofrece sola (`web.js` toma el `.exe` de la release más reciente). **La v0.6.1 está cerrada.**
- Web ampliada (2026-11-28): franja de cifras, tabla «Qué puedes hacer con cada cable», sección «Coches y centralitas compatibles» (21 módulos, 50 PIDs y grupos de los 3 motores, sacados de las tablas del programa), filas «Diésel y gasolina VAG» y «Manual dentro del programa» con capturas nuevas (`panel-gasolina`, `valores-gasolina`, `ayuda`, hechas por `web/capturas.py`) y «Novedades por versión». **Al sacar una versión, añadir su bloque en `#novedades` de las dos páginas.**

### 8.2e Test de actuadores (2026-11-28, sin publicar)
- Botón «Test de actuadores...» en Averías (solo KKL) → ventana `VentanaActuadores` (`gui.py`): avisos, casilla «He leído los avisos…» obligatoria, «Iniciar» / «Siguiente componente» / «Terminar», componente activo con el tiempo que lleva y lista de los probados. La ventana es modal y la IA no puede leer ni borrar mientras está abierta (`act_en_curso`).
- Protocolo (`KW1281.actuator_test`): bloque 0x04 con un byte 0x00 (como kw1281test); la centralita contesta 0xF5 con el código del componente (numeración de averías VAG: 01265 = EGR N18) y lo activa hasta la petición siguiente; ACK o código 0000/FFFF = fin. Si la primera petición da NAK se reintenta sin el byte de datos. NAK = no tiene el test o no se cumplen las condiciones (motor parado, contacto puesto).
- «Terminar» a mitad: se cierra la sesión (0x06) y se vuelve a conectar, para que la centralita apague el componente.
- Simulador: secuencia del TDI (K29, EGR N18, N75, N109), del gasolina (bomba, 4 inyectores, N80, EGR), ABS (bomba V64) y cuadro; el airbag contesta NAK. Pruebas en `prueba_simuladores.py` y `prueba_gui.py` (español e inglés) → «TODO CORRECTO».
- **Probado en coche por el usuario (2026-11-28): funciona bien.** Dudas que había antes de probarlo: si espera el byte 0x00, cómo marca el final y si cerrar la sesión apaga el componente.

### 8.2f Ajustes básicos (2026-11-28, sin publicar)
- Botón «Ajustes básicos...» en Averías (solo KKL) → ventana `VentanaAjustes` (`gui.py`), modal y con la IA bloqueada igual que el test de actuadores. Se elige un ajuste habitual del motor (`vag_datos.ajustes_basicos`: TDI EDC15 004 comienzo de inyección y 003 EGR desactivada; PD 003; gasolina 098 y 060 adaptación de la mariposa y 001 ajuste básico del motor) o se escribe un número de grupo 1-254; casilla «Se cumplen las condiciones de este ajuste» obligatoria; valores en vivo con los nombres del grupo y el tiempo que lleva.
- Protocolo (`KW1281.basic_setting`): bloque 0x28 con el grupo, repetido unas 4 veces por segundo mientras dura (`Worker._read_basico`); respuesta 0xE7 (como un grupo) o 0xF4 (si son ternas con fórmulas conocidas se decodifican; si no, se muestran los bytes en bruto). «Salir del ajuste básico» (y cerrar la ventana) hace una lectura normal del grupo (0x29), que saca a la centralita del modo de ajuste básico.
- Simulador: grupo 003 con la EGR a 0 en ajuste básico, grupo 004 del TDI, 098 de gasolina (respuesta 0xF4) que termina la adaptación a los 3 s; los grupos que no tiene → NAK. Pruebas en `prueba_simuladores.py` y `prueba_gui.py` (español e inglés) → «TODO CORRECTO».
- **Probado en coche por el usuario (2026-11-28): funciona bien.** Dudas que había antes de probarlo: qué título usa la EDC15 al contestar (E7 o F4), que la lectura normal la saque del ajuste básico y los textos de estado de la adaptación de la mariposa (salen como bits o `a=.. b=..` si la fórmula no está en la tabla).
- Canales de adaptación y codificación: hechos después, ver §8.2h.

### 8.2h Adaptación y codificación (2026-11-28, v0.8.0 y v0.8.1)
- Botón «Adaptación...» en Averías (solo KKL) → ventana `VentanaAdaptacion` (`gui.py`), modal y con la IA bloqueada (`act_en_curso`) como las de actuadores y ajustes. Avisos y casilla «He leído los avisos y tengo los valores del manual de taller» obligatoria para escribir (leer no la pide).
- **Canal de adaptación**: «Leer» (valor guardado) → escribir el valor nuevo → «Probar» (la centralita lo usa sin guardarlo) → «Guardar» (solo se activa tras probar ese mismo valor; pide confirmación con antes/ahora). Si se prueba un valor y se cierra la ventana o se lee otro canal sin guardar, se vuelve a probar el valor guardado. El canal 00 (borra todas las adaptaciones) no se permite (1-255).
- **Código de acceso (login)** opcional, para los canales o centralitas que lo piden. **Codificación**: muestra la actual y el código de taller (de la identificación); «Guardar codificación» con confirmación; la centralita contesta con su identificación y se comprueba que trae la codificación nueva (si no, error). Vehículo se actualiza. Si la centralita no informa de su codificación, no se deja cambiar. **Código de taller**: por defecto el que tiene la centralita; se manda con cada cambio.
- **Registro de cambios** (`cambios.py`): cada canal o codificación guardados se apuntan con el valor de antes en `cambios_centralita.jsonl` de la carpeta de configuración (se añade, nunca se reescribe; aguanta líneas cortadas). La ventana lista los de esa centralita (módulo + referencia) y «Volver al valor anterior» rellena el valor de antes para probarlo y guardarlo con el flujo normal.
- Protocolo (`kw1281.py`, comprobado con el código de kw1281test, licencia MIT): lectura 0x21 [canal], prueba 0x22 [canal, valor 2 bytes], guardado 0x2A [canal, valor, taller 3 bytes], respuesta 0xE6 [canal, valor]; login 0x2B [código 2 bytes, taller 3 bytes] → ACK o NAK; codificación 0x10 [codificación×2 (+1 si taller > 65535), taller 2 bytes] → bloques 0xF6 de identificación. La codificación se lee del bloque 0xF6 que empieza por 0x00: codificación = (b1·256 + b2) / 2, taller = b3·256 + b4 (+65536 si b2 es impar).
- Simulador: motor con canales 01 (128, rango 118-138) y 02 (32768, con login), cuadro con 02 y 09 (con login); código de acceso del simulador 11111; el motor y el cuadro tienen codificación (el motor acepta hasta 16383, para probar un rechazo), el ABS no. Lo guardado sobrevive a la reconexión; el login no. **No son canales ni rangos reales.**
- Pruebas en `prueba_simuladores.py`, `prueba_historial.py` y `prueba_gui.py` (español e inglés) → «TODO CORRECTO». El ancho mínimo de la ventana tiene en cuenta ahora la barra de Averías con el botón nuevo. **Probado por el usuario en coche (2026-11-28): todo bien.** Dudas que había antes de probarlo: que conteste 0xE6 a la prueba (0x22) y al guardado, y qué hace la centralita tras cambiar la codificación (si reenvía la identificación o reinicia la sesión).

### 8.2i Release v0.8.0 y v0.8.1 (2026-11-28)
- Adaptación y codificación (§8.2h), probadas en coche por el usuario antes de etiquetar. `VERSION = "0.8.0"`. Pruebas: simuladores, idioma, consumo, csv, historial y GUI en español e inglés → «TODO CORRECTO».
- Etiqueta `v0.8.0` → `94a3cb8`. Paquete `OBD2Desk-v0.8.0-linux-x86_64.tar.gz` (40 593 260 bytes, SHA-256 `113f63ca96cba5372705654ddf94cc2b245951d4d840634bcad1290c44c99766`): autoprueba IA bien, abre la ventana; descargado de GitHub con el mismo SHA-256. Release «OBD2Desk v0.8.0» con notas en español e inglés.
- Al hacer las capturas de la web se vio que el botón «Volver al valor anterior» se cortaba en inglés (tenía `width=24`). **v0.8.1**: sin ancho fijo, y `prueba_gui.py` comprueba que ningún botón de la ventana de adaptación corte su texto (`botones_cortados`, mide el texto con la fuente y el relleno del estilo; comprobado que detecta el fallo). Etiqueta `v0.8.1` → `87b8e5a`. Paquete `OBD2Desk-v0.8.1-linux-x86_64.tar.gz` (40 593 871 bytes, SHA-256 `859b0f8ffb3b1565eb3e7bd02f2d46f4d057d170704bc1e15d24e21d48f8a647`): autoprueba IA bien, abre la ventana; descargado de GitHub con el mismo SHA-256. Release «OBD2Desk v0.8.1» «Latest»; las notas de la v0.8.0 remiten a la v0.8.1 para el `.exe` (no se compila para la v0.8.0).
- `.exe` de Windows subido después (27 777 511 bytes, SHA-256 `1de8440220bb0a0b9bab3887b621cea7e1386eaa8e017130301b678db609de73`), compilado desde `85820dc` (mismo código que `v0.8.1`; solo cambian web y documentación); descargado de GitHub con el mismo SHA-256; notas sin «en breve». La web ya lo ofrece (lo elige `web.js`). **Probado en Windows por el usuario: funciona bien. v0.8.1 cerrada.**
- Web: artículo «Adaptación y codificación» con captura nueva (`adaptacion`, hecha por `web/capturas.py`), fila de la tabla de cables con ✓, bloques v0.8.0 y v0.8.1 en `#novedades`, estado (verificado en coche; quitado «no escribe canales de adaptación ni codificación»); quitado «Nuevo» y «pendiente de probar en coche» del artículo de actuadores. El ancho mínimo nuevo hace las capturas en español de 2074 px (antes 2025): `width` de las imágenes actualizados.

### 8.2g Release v0.7.0 (2026-11-28)
- Test de actuadores (§8.2e) y ajustes básicos (§8.2f). `VERSION = "0.7.0"`. Pruebas antes de etiquetar: simuladores, idioma, consumo, csv, historial y GUI en español e inglés → «TODO CORRECTO». Después, probada en coche por el usuario: funciona bien.
- Etiqueta `v0.7.0` → `58d47ee`. Paquete `OBD2Desk-v0.7.0-linux-x86_64.tar.gz` (40 572 636 bytes, SHA-256 `3828662ad598842e3afda83741225af95735931ebcb97cbadd1a4d9f870e896b`): autoprueba IA bien (3 proveedores «no válida»); extraído, abre la ventana. Descargado de GitHub con el mismo SHA-256.
- Release «OBD2Desk v0.7.0» «Latest» con notas en español e inglés; dicen que el `.exe` llega en breve (enlazan el de la v0.6.1; la web también ofrece el de la v0.6.1 mientras tanto). `.exe` de Windows subido después (27 755 201 bytes, SHA-256 `10e13765e27764b9650f47b3304a6c2c952e56cbb18bd24687ac2686030dfe3b`), compilado desde `2cf76cb` (mismo código que `v0.7.0`; solo cambian web y documentación); descargado de GitHub con el mismo SHA-256; notas sin «en breve». La web ya lo ofrece (lo elige `web.js`). **Probado en Windows por el usuario: funciona bien. v0.7.0 cerrada.** Test de actuadores y ajustes básicos **probados en coche por el usuario (2026-11-28): funcionan bien**; web y notas de la release lo dicen.
- Web publicada (`./web/publicar.sh "Web v0.7.0: ..."`): artículo «Test de actuadores y ajustes básicos» con capturas nuevas (`actuadores`, `ajustes`, hechas por `web/capturas.py`), fila en la tabla de cables, bloque v0.7.0 en `#novedades` y estado; quitado «Nuevo» de los artículos de la v0.6.0; todas las capturas rehechas.

### 8.3 Cómo sacar la próxima versión (lista de pasos)
Resumen de lo que funcionó con la v0.2.0 y la v0.3.0:
1. Fedora: cambiar `VERSION` en `gui.py`; `.venv/bin/python tests/prueba_simuladores.py`, `.venv/bin/python tests/prueba_idioma.py`, `xvfb-run -a .venv/bin/python tests/prueba_gui.py` y `OBD2DESK_IDIOMA=en xvfb-run -a .venv/bin/python tests/prueba_gui.py` → «TODO CORRECTO» (las dos de GUI una detrás de otra: a la vez chocan en el nombre del CSV).
2. Commit, `git tag -a vX.Y.Z -m "..."`, `git push && git push --tags`.
3. `./linux/build-portable.sh vX.Y.Z` (hace la autoprueba IA); extraer el `.tar.gz` y abrirlo.
4. `gh release create vX.Y.Z dist/OBD2Desk-vX.Y.Z-linux-x86_64.tar.gz --title "OBD2Desk vX.Y.Z" --notes-file notas.md` (si el `.exe` aún no está, decirlo en las notas).
5. Windows: `git pull`, `git fetch --tags --force`, `git checkout vX.Y.Z`, `build.bat`, `git checkout main`; probar simuladores, `--autotest-ia` y abrir el `.exe`. Anotar tamaño y SHA-256 (`certutil -hashfile dist\OBD2Desk.exe SHA256`).
6. Fedora: copiar el `.exe` desde la partición de Windows (`/run/media/jaso/D8AE878DAE87633C/Users/jose/Desktop/obd2/dist/`), comprobar SHA-256, `gh release upload vX.Y.Z OBD2Desk.exe`, ajustar las notas, descargarlo de GitHub y volver a comprobar el SHA-256.
7. Web: textos (las dos páginas, `web/index.html` y `web/en/index.html`) y capturas (`web/capturas.py` y `web/capturas.py en`) con las funciones nuevas; `./web/publicar.sh`. Los botones de descarga se actualizan solos (`web.js` lee la API de GitHub).
8. Actualizar `CLAUDE.md` (Estado) y este documento.

## 9. Estado actual y limitaciones (ser honesto en la web)
- **Probado**: todo contra los simuladores; IA contra la API real (Claude) con el simulador; ejecutable de Windows; en Linux, el código y la GUI en Fedora 44 y el paquete portable en contenedores de Ubuntu 20.04/24.04, Debian 12, Fedora 40/44, Arch y openSUSE Leap 15.6 (instala, autoprueba IA y abre la ventana).
- **Probado en coches reales** (un par de coches, noviembre 2026, v0.2.0; y la v0.3.0 el 2026-11-22): funciona bien. La web lo dice.
- **Probado por el usuario (anotado el 2026-11-28)**: en Linux, los adaptadores físicos (cable FTDI con `dialout`, ELM327 Bluetooth con `rfcomm`) y el lanzador en un escritorio real.
- Ajustes probables al probar con coche: tiempos entre bytes (`--retardo` en consola), alguna fórmula VAG, textos de averías.
- **v0.3.0 probada en coche** (2026-11-22, el usuario: «funciona bien»); la web lo dice. ELM327 WiFi real, v0.6.0 en coche (gasolina VAG y PD), consumo diésel por OBD2 y 0-100 con ELM327 real: probados por el usuario (anotado el 2026-11-28); la web ya no muestra pendientes.
- Tabla de averías VAG: unos 90 códigos clásicos (00xxx-01xxx) de motor, cambio, ABS, airbag, cuadro/inmovilizador, confort y radio, más los códigos en formato OBD (16xxx = P0xxx, que se describen con la tabla OBD2; 17xxx-18xxx = P1xxx, 538 en la tabla `vag_p1.py` desde la v0.6.0). Los demás salen con número y «no incluido en la tabla». Ampliada el 2026-11-22 en la v0.3.0 (publicada, web actualizada).
- La lista de fórmulas VAG viene de documentación pública del protocolo; si una fórmula no se conoce se muestra `a=.. b=..`.
- Desde la v0.7.0: test de actuadores y ajustes básicos (probados en coche). Desde la v0.8.0: canales de adaptación y codificación (§8.2h, probados en coche).

## 10. Próximos pasos (actualizado el 2026-11-28)
Por orden de prioridad propuesto; el usuario decide por dónde seguir.

**1. Pequeños pendientes (para la próxima versión, sea cual sea)**
- ~~Probar con un **ELM327 WiFi real**~~ **probado por el usuario** (anotado el 2026-11-28); quitada de la web la línea de pendiente.
- ~~Probar en coche la v0.6.0 (gasolina VAG, TDI PD), el consumo de un diésel por OBD2 y el 0-100 con un ELM327 real~~ **probado por el usuario** (anotado el 2026-11-28); la web ya no lo da como pendiente.
- ~~Mover «Consumo y 0-100» tras «Vehículo» y añadir la pestaña «Ayuda»~~ **hecho el 2026-11-28** (sin publicar; probado con `prueba_gui.py` en español e inglés).
- ~~En Linux, probar los adaptadores físicos (cable FTDI con `dialout`, Bluetooth con `rfcomm`) y el lanzador en un escritorio real~~ **probado por el usuario** (anotado el 2026-11-28).

**2. Bloque 2 de funciones (propuesto el 2026-11-22, candidato a v0.5.0)**
- ~~Consumo instantáneo y medio y cronómetro 0-100 km/h~~ **hecho el 2026-11-27** (pestaña «Consumo y 0-100», sin publicar; probado solo con simuladores: falta probarlo en coche, sobre todo el consumo de un diésel por OBD2 y el 0-100 con un ELM327 real, que da 5-10 lecturas/s).
- ~~Gráfica de cualquier valor en vivo y abrir/ver un CSV grabado~~ **hecho el 2026-11-27** (en «Valores medidos»; sin publicar; probado con simuladores).
- ~~Historial por coche (por VIN): guardar cada diagnóstico y comparar~~ **hecho el 2026-11-27** (sin publicar; probado con simuladores).
- ~~Más herramientas para la IA~~ **hecho el 2026-11-27**: `grabar_valores`, `consultar_historial`, `generar_informe` (sin publicar; probadas con simuladores llamándolas como el modelo y **con la API real de DeepSeek** (`deepseek-chat`, 2026-11-27, ~1 min): usó `consultar_historial`, `grabar_valores` (3 grabaciones de 10 s porque esperaba el motor caliente) y `generar_informe`; informe con su diagnóstico y la comparación, bien. Con Anthropic no se ha probado: el usuario solo tiene clave de DeepSeek guardada).

**3. Más adelante**
- ~~Más P1 de VAG y grupos de TDI inyector-bomba y gasolina~~ **hecho el 2026-11-28** (538 P1, también en OBD2 si el VIN es VAG; grupos PD del manual de taller y de gasolina estándar de Ross-Tech; sin publicar, probado con simuladores). Falta: averías de confort/clima (no se encontró una tabla pública fiable). Panel y consumo KKL para gasolina **hechos el 2026-11-28** (sin publicar; probados con el simulador de gasolina: `simulador.GASOLINA = True`, ident «1.8L R4/5VT», grupos 1-5).
- Firma del ejecutable de Windows (evitar SmartScreen).
- ~~Test de actuadores KW1281~~ **hecho el 2026-11-28** (§8.2e). ~~Ajustes básicos~~ **hechos el mismo día** (§8.2f). Publicados en la v0.7.0 y probados en coche. ~~Canales de adaptación y codificación~~ **hechos el 2026-11-28** (§8.2h), publicados en la v0.8.0 y probados en coche.
- Adaptador inalámbrico propio con ESP32 haciendo KW1281. **Al usuario le gusta (tiene muchos ESP32); lo hará aparte, en jasodev.es** (anotado el 2026-11-28). Falta mirar el conector OBD2 (pines: 7 línea K, 16 +12 V, 4/5 masa). Idea: transceptor L9637D/MC33290, el ESP32 hace todo el KW1281 y OBD2Desk le habla por WiFi/BT con órdenes de alto nivel; primer paso, probar el init de 5 baudios con el Toledo.

**Más marcas (propuesto el 2026-11-28 por amigos y familiares del usuario)**: el ELM327 ya vale para cualquier marca, pero solo describía 107 P0. Tres niveles: (1) tabla completa de códigos genéricos y web para cualquier marca; (2) escanear todas las centralitas en coches con CAN (UDS con ELM327; direcciones por marca, **hay que probarlo en coches reales**: preguntar al usuario qué coches tiene su gente); (3) funciones propias de cada marca (no recomendado). **Nivel 1 hecho el 2026-11-28, sin publicar**: `obd_codigos.py` (9533 códigos, ver §7.1) y páginas web `/codigos-obd2/` y `/en/obd2-codes/` (40 listas por idioma con buscador; la lista VAG 16xxx = P0 pasa a los 1000 P0 numéricos). Al sacar la versión: anunciarlo en la portada (cifras, tarjeta del ELM327, tabla de cables, «Compatibles», novedades).

**Hecho el 2026-11-27 (publicado en la v0.4.0):** renombrado a **OBD2Desk** (dominio obd2desk.com) e interfaz en inglés.

**Aparcado (no sacarlo por iniciativa propia):** versión para Mac (sin Mac para probar; plan con GitHub Actions).

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

**Estado (2026-11-27): la web usa ya el nombre OBD2Desk y su dominio https://obd2desk.com**, en español e inglés (código en `web/` de este repositorio). El programa se renombró a OBD2Desk el 2026-11-27 (en `main`; sale en la próxima versión). Hasta el 2026-11-27 se publicaba en https://www.jasodev.es (repo `jaso69/jasodev`).
- `web/index.html` (español, una sola página con las secciones de §12.2), `web/en/index.html` (inglés, misma estructura; rutas con `../`; usa las capturas de `img/en/` y nombra los botones en inglés), `web/estilo.css` (colores de §7.5, fuentes del sistema, sin recursos de terceros), `web/web.js` (menú móvil, selector KKL/OBD2 de capturas, visor ampliado, enlaces de descarga y textos según `<html lang>`).
- Idioma: botón ES/EN en el menú (`data-idioma`, guarda la elección en `localStorage`). `web/idioma.js` (solo en la página en español, en `<head>`): la primera visita de un navegador sin español/catalán/gallego/euskera va a `/en/`; respeta la elección guardada y no redirige a los buscadores. `hreflang` en ambas páginas y en `sitemap.xml`. Al cambiar un texto, cambiarlo en las dos páginas.
- Descargas: `web.js` consulta `api.github.com/repos/jaso69/obd2/releases` (incluye pre-releases, que `releases/latest` ignora) y apunta los botones al `.exe` y al `*linux*.tar.gz` de la última release; sin JS o sin paquete, llevan a la página de releases.
- Capturas: `xvfb-run -a -s "-screen 0 2400x1500x24 -dpi 144" python3 web/capturas.py` → `web/img/*.webp` + `og.jpg` (1200×630 para redes). Usa los simuladores en una pantalla virtual; en la conversación de IA solo se sustituye la llamada al modelo por un guion (herramientas reales, texto de ejemplo coherente con los datos del simulador; la web lo aclara). `python3 web/capturas.py en` genera las capturas en inglés en `web/img/en/` (las usa `web/en/index.html`). Regenerar si cambia la interfaz.
- Ver en local: `python3 -m http.server -d web 8000` → http://127.0.0.1:8000 (y `/en/`).
- Publicación: `./web/publicar.sh ["mensaje"]` sustituye el contenido del repositorio https://github.com/jaso69/obd2desk (rama `main`, enlazado con Vercel, dominio `www.obd2desk.com`; `obd2desk.com` redirige con 308; canónicas y sitemap con `www`) por `web/` (sin `capturas.py` ni `publicar.sh`) y lo sube con un commit normal; Vercel la publica en segundos.
- `web/vercel.json`: `trailingSlash`, cabeceras de seguridad (CSP sin scripts ni estilos en línea; `connect-src` permite `https://api.github.com` para los botones de descarga) y caché de `img/`. Si se añade un script o estilo en línea al HTML, la CSP lo bloqueará. `robots.txt` y `sitemap.xml` apuntan a `obd2desk.com`.


**Web de la v0.5.0 publicada (2026-11-27)**: bloques nuevos «Consumo y cronómetro 0-100» e «Historial de cada coche», «Valores medidos, gráficas y grabación» con selector «Gráfica en vivo / Visor de CSV», pasos del asistente con historial e informe, estado con las novedades «probadas con los simuladores; pendientes de verificar en coche». Capturas regeneradas (miden 2025×1200 en español y 2015×1200 en inglés: la pestaña nueva ensancha la ventana; los `width` del HTML lo reflejan). **Publicarla solo cuando exista la release v0.5.0** (si no, anuncia funciones que la descarga no trae); si se prueba en coche antes, quitar la línea «pendientes de verificar en coche».

**Revisión de SEO, semántica y accesibilidad (2026-11-28)**: axe-core (WCAG 2.2 AA + buenas prácticas) sin fallos en las dos páginas, en escritorio y móvil. Hecho: descripción de 160 caracteres, sin `keywords`, `og:site_name`/`og:image:*`, `apple-touch-icon`, JSON-LD `SoftwareApplication` (la CSP no lo bloquea: no se ejecuta), enlace «Saltar al contenido», `nav` con nombre, títulos de las tarjetas de portada en `h2` (`.tarjeta-titulo`), selectores de capturas como grupo de botones con `aria-pressed` (no pestañas), tabla de cables con «Sí/No» para lectores de pantalla y región desplazable con foco, enlaces del texto subrayados, `code` con contraste suficiente, símbolos decorativos ocultos (`aria-hidden`, `content: "✓" / ""`), fechas de novedades en `<time>`, `fetchpriority` en la captura de portada, `sitemap.xml` con `lastmod` al día. Al tocar la web, mantener esto.

**Códigos OBD2 genéricos (2026-11-28)**: `generar_paginas.py` crea también `/codigos-obd2/` y `/en/obd2-codes/` desde `obd_codigos.py`: índice (cómo se lee un código, buscador, fuente OBDex) y 40 listas (P00-P0E, P20-P2E, P34, B0, C0, U00-U06, U3); en español, descripción revisada si la hay, si no la traducción automática y, si falta, el inglés con `lang="en"`. `codigos.json` con enlaces relativos (≈1 MB, 120 KB comprimido; se carga al escribir en el buscador). Menú de las páginas secundarias: «Códigos OBD2». Sitemap: 114 URL.

**Buscadores (2026-11-28)**: Google Search Console verificado (TXT en el DNS de Vercel) y sitemap enviado por el usuario. Bing por **IndexNow**: clave en `web/<clave>.txt` (se publica) y `./web/indexnow.sh` (no se publica) envía todas las URL del sitemap; ejecutarlo después de `./web/publicar.sh` cuando haya páginas nuevas o cambiadas. Bing Webmaster Tools dado de alta por el usuario (importado desde Search Console, con el sitemap).

**Páginas de códigos de avería VAG (2026-11-28)**: `web/generar_paginas.py` (no se publica) crea, desde las tablas del programa (`vag_datos.DTCS`, `vag_p1.P1`, `obd_datos.DTCS` y `textos_en.EN`), 11 páginas por idioma: índice (`/averias-vag/`, `/en/vag-fault-codes/`) con cómo se leen los códigos, tipos de fallo y buscador; clásicos por sistema; 16xxx = P0; y P11xx-P18xx. 738 códigos. Cada fila tiene ancla con el código VAG (`#17978`) y el P (`#P1570`). Buscador en `web/averias.js` (carga `codigos.json` al escribir). También reescribe `sitemap.xml` entero (cambiar `FECHA` en el script). **Volver a ejecutarlo si cambian las tablas de averías.** Enlazadas desde la portada (Averías, Compatibles y pie). axe sin fallos; enlaces y anclas comprobados.

**SEO (2026-11-28)**: `<title>` con las palabras que se buscan («OBD2Desk · Diagnosis OBD2 y VAG con cable KKL, gratis» / «OBD2Desk · Free OBD2 and VAG KKL car diagnostics»); el `og:title` sigue con la frase de portada. Repositorio de GitHub con descripción, web y temas. Hecho después: Search Console, Bing Webmaster y páginas de códigos de avería (ver arriba). **SEO técnico terminado (2026-11-28)**: guías en `/guias/` y `/en/guides/` (cable KKL, ELM327 Bluetooth/WiFi, grupos del 1.9 TDI; texto en `web/guias.py`, tablas de grupos sacadas de `vag_datos.py`, JSON-LD `TechArticle`) enlazadas desde la portada; `404.html` bilingüe con `noindex`; capturas de 1000 px (`*-1000.webp`, las crea `capturas.py`) con `srcset`/`sizes` en la portada (el selector de `web.js` actualiza también el `srcset`). `generar_paginas.py` (antes `generar_averias.py`) genera averías, guías, 404 y `sitemap.xml` (32 URL); `publicar.sh` excluye todos los `.py`. Pendiente solo del usuario: enlaces desde foros, Reddit y AlternativeTo.

**Sección «Estado del proyecto» (`#estado`) quitada de la web el 2026-11-28** a petición del usuario (ya no tenía pendientes). Lo que queda por probar ya no se cuenta en la web; si hiciera falta avisar de algo sin probar, decirlo en el artículo de la función o en las notas de la release.

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
- Consumo y 0-100 (ELM327, con un 0-100 medido: `capturas.py` adelanta el reloj del simulador), Valores medidos con la gráfica de turbo teórico/real, visor de CSV (30 s grabados, ratón encima) e Historial (lectura + borrado). Las ventanas secundarias se capturan al tamaño de la principal.
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
«OBD2Desk es software libre bajo licencia MIT y un proyecto independiente, sin relación con SEAT, Volkswagen
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
