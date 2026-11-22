# Toledo Diagnosis - VAG KW1281 + OBD2 (ELM327)

**Web: https://www.jasodev.es** · descargas, guía de uso y qué cable comprar.

Dos modos de conexión, elegibles en la parte superior de la ventana:

- **KKL · VAG KW1281**: centralita Bosch EDC15 del SEAT Toledo II 1.9 TDI (2000) y
  otros módulos VAG hasta ~2004, por línea K con un cable **KKL 409.1 FTDI**.
- **ELM327 · OBD2 genérico**: cualquier coche con OBD2/EOBD (gasolina desde 2001,
  diésel desde ~2004) con un ELM327 USB o **Bluetooth** (al emparejarlo se crea
  un puerto COM o `/dev/rfcomm0`; ver [Conectar un ELM327 Bluetooth](#conectar-un-elm327-bluetooth)).
  Lee PIDs estándar, averías memorizadas y pendientes (P0xxx), testigo MIL,
  VIN y tensión de batería, y permite borrar averías. Si la búsqueda automática
  de protocolo falla, prueba uno a uno los de línea K (KWP2000 rápido y lento,
  ISO 9141-2), útil en coches anteriores a CAN como Mercedes antiguos.

## Archivos

| Archivo | Qué es |
|---|---|
| `docs/PROYECTO.md` | **Documentación completa** (uso, hardware, IA, arquitectura, guion de la web) |
| `Toledo Diagnosis.pyw` | **Doble clic** (Windows): abre la interfaz gráfica |
| `build.sh`, `linux/` | Ejecutable, paquete para distribuir e instalación en Linux |
| `tests/prueba_simuladores.py` | Pruebas de protocolo contra los simuladores |
| `tests/prueba_gui.py` | Prueba de la interfaz con los dos simuladores |
| `web/` | Web del proyecto (https://www.jasodev.es); `web/publicar.sh` la sube |
| `gui.py` | Interfaz gráfica (panel con relojes y gráficas, valores, averías, CSV) |
| `toledo.py` | Versión de consola (menú de texto) |
| `kw1281.py` | Protocolo KW1281: init 5 baudios, bloques, complementos, keep-alive |
| `elm327.py` | OBD2 por ELM327: protocolo automático (y prueba de línea K si falla), CAN multi-trama, multi-PID, averías, VIN |
| `obd_datos.py` | PIDs OBD2 estándar y descripciones de averías P0xxx |
| `ia.py` | Asistente IA: Anthropic / OpenAI / DeepSeek, claves cifradas, prompt de diagnosis |
| `vag_datos.py` | Fórmulas de valores medidos, averías VAG, grupos EDC15 |
| `simulador.py` | Cable KKL + EDC15 y ELM327 + coche OBD2 simulados para probar sin coche |
| `sonda_toledo.py` | Sonda para adaptador ELM327 (solo si quieres comprobar qué responde con él) |

## Asistente IA (pestaña «✦ Asistente IA»)

Diagnóstico guiado con IA: describe el síntoma («le falta potencia y echa humo
negro») y la IA hace las comprobaciones que crea necesarias con herramientas:

- `estado_conexion`, `leer_averias`, `leer_valores` (grupos VAG o PIDs OBD2, con
  series de hasta 40 muestras), `borrar_averias` (siempre con confirmación del
  usuario) y `leer_registro`.
- `pedir_accion_usuario`: ventana con la instrucción (arrancar, acelerón en vacío…)
  y botones «Hecho» / «No puedo».
- Máximo 15 rondas de comprobaciones por mensaje; luego la IA debe concluir.
- Normas de seguridad en el prompt: pruebas en parado; en marcha solo con acompañante.

También analiza el registro del programa cuando falla la comunicación y admite
preguntas de seguimiento.

- Proveedores: **Anthropic (Claude)** por defecto (`claude-opus-5-5`), **OpenAI**
  (`gpt-5`) y **DeepSeek** (`deepseek-chat`). El modelo se puede cambiar.
- Necesita una API key del proveedor (enlace «Conseguir una API key» en la pestaña).
  Se guarda cifrada (DPAPI de Windows) en `%APPDATA%\ToledoDiagnosis\config.json`;
  solo vale para ese usuario y equipo, así que en el portátil hay que introducirla de nuevo.
- Se envían al proveedor: datos del vehículo/centralita (incluido el VIN), averías,
  últimos valores medidos y, en «Analizar errores del programa», el registro.
- Cada consulta tiene un coste pequeño en la cuenta del proveedor.
- Con Claude Opus 5.5 / Sonnet 5.5 se activa el reintento automático en otro modelo
  si el modelo declina responder (`fallbacks: "default"`).

## Instalación en Linux (paquete)

Descarga `ToledoDiagnosis-<versión>-linux-x86_64.tar.gz` de
[Releases](https://github.com/jaso69/obd2/releases/latest) (Ubuntu 20.04+, Debian 11+,
Mint 20+, Fedora, openSUSE, Arch... 64 bits):

```
tar xzf ToledoDiagnosis-*-linux-x86_64.tar.gz
cd ToledoDiagnosis && ./instalar.sh        # sin sudo; --desinstalar para quitarlo
sudo usermod -aG dialout $USER             # permiso para el cable (Arch: uucp); cerrar sesión
```

Las grabaciones CSV van a `Documentos/ToledoDiagnosis`. Más detalles en el `LEEME.txt` del paquete.

## Instalación desde el código

```
pip install -r requirements.txt
```

## Ajuste recomendado del driver FTDI (importante)

KW1281 confirma cada byte en pocos milisegundos. El driver FTDI retiene los datos
16 ms por defecto, lo que puede provocar cortes:

Administrador de dispositivos → Puertos (COM y LPT) → USB Serial Port →
Propiedades → Configuración de puerto → Opciones avanzadas →
**Temporizador de latencia: 1 ms**. Apunta también el número de COM.

## Conectar un ELM327 Bluetooth

Un ELM327 Bluetooth funciona como un **cable serie sin cable**: al emparejarlo, el
sistema crea un **puerto serie virtual** (un COM en Windows, `/dev/rfcomm0` en Linux)
y el programa habla con él igual que con un adaptador USB. Por eso en el programa no
se busca «el Bluetooth»: se elige **ese puerto**. Primero se empareja desde el
sistema y después se conecta desde el programa.

**Windows 10 y 11**

1. Enchufa el ELM327 al coche y pon el contacto (se enciende su luz).
2. *Configuración → Bluetooth y dispositivos → Agregar dispositivo → Bluetooth* y
   elige el adaptador (suele llamarse OBDII, OBD2 o V-LINK). PIN habitual: `1234`,
   `0000` o `6789`.
3. Mira qué puerto le ha dado: *Más opciones de Bluetooth → pestaña Puertos COM*, el
   de dirección **Saliente** (p. ej. COM5). También sale en *Administrador de
   dispositivos → Puertos (COM y LPT)* como «Vínculo serie estándar a través de Bluetooth».
4. En el programa: *Conexión* ELM327, *Puerto* ese COM y *Conectar* (suele
   preseleccionarlo).

Es normal que Windows lo muestre como «Emparejado» y no «Conectado»: la conexión se
abre al pulsar *Conectar*. Si hay dos COM y uno no responde, prueba el otro.

**Linux**

```
bluetoothctl                          # dentro: scan on, pair <MAC>, trust <MAC>, quit
sudo rfcomm bind 0 AA:BB:CC:DD:EE:FF  # crea /dev/rfcomm0 (repetir tras reiniciar)
```

También se puede emparejar desde los ajustes de Bluetooth del escritorio; el
`rfcomm bind` hace falta igualmente. Después, en el programa: *Conexión* ELM327,
*Puerto* `/dev/rfcomm0` y *Conectar*. Si no tienes `rfcomm`: Fedora
`bluez-deprecated`, Arch `bluez-deprecated-tools` (Debian/Ubuntu/Mint ya lo traen en `bluez`).

El ELM327 solo admite una conexión a la vez: cierra la app del móvil (Torque, Car
Scanner...) o apaga su Bluetooth antes de conectar desde el ordenador.

## Uso

```
python toledo.py --sim          # probar con el simulador
python toledo.py COM3           # motor (dirección 01)
python toledo.py COM3 --modulo 17   # cuadro; 03 ABS, 15 airbag, 08 clima...
python toledo.py COM3 --debug   # muestra cada bloque enviado/recibido
```

Contacto puesto. La conexión prueba 10400 y 9600 baudios automáticamente
(`--baudios 9600` para fijar uno). Si da errores de complemento o de eco, prueba
`--retardo 5`.

Menú: identificación, leer/borrar averías, valores medidos en vivo (varios grupos
a la vez, p. ej. `1,3,11`) y registro a CSV (separador `;`, abre en Excel).

## Grupos útiles en 1.9 TDI EDC15 (orientativo)

- **001** régimen, caudal inyectado (mg/H), tensión dosificador, temp. refrigerante
- **003** régimen, masa de aire teórica/real (mg/H), ciclo EGR → caudalímetro y EGR
- **004** comienzo de inyección teórico/real (motores de bomba rotativa)
- **011** régimen, presión turbo teórica/real (mbar), ciclo N75 → turbo
- **013** marcha suave por cilindro (si lo soporta)

Los nombres de los campos son orientativos; la unidad la calcula el programa con
la fórmula que envía la propia ECU. Si una fórmula no está en la tabla se muestra
`a=.. b=..` con `?` al lado.

## Problemas típicos

- **Sin byte 0x55**: contacto quitado, COM equivocado, cable CH340 en vez de FTDI,
  o radio no original bloqueando la línea K (desconéctala para probar).
- **Keywords KWP2000**: la ECU no habla KW1281; habría que usar el ELM327.
- **Se corta la conexión**: latencia FTDI a 1 ms, prueba `--retardo 3`.
- **No encuentro el puerto del ELM327 Bluetooth**: hay que emparejarlo y elegir el
  puerto serie que crea el sistema (ver [Conectar un ELM327 Bluetooth](#conectar-un-elm327-bluetooth)).

## Licencia

MIT. Ver [LICENSE](LICENSE). Proyecto independiente, sin relación con SEAT, Volkswagen Group ni los fabricantes de los adaptadores; se ofrece sin garantía.
