"""
Asistente de IA de diagnosis con herramientas: la IA puede leer averias y
valores medidos, pedir acciones al usuario y hacer las comprobaciones que crea
necesarias hasta llegar a un diagnostico.

Proveedores: Anthropic (Claude, por defecto), OpenAI y DeepSeek.
- Anthropic: SDK oficial `anthropic` (Messages API con herramientas).
- OpenAI / DeepSeek: SDK `openai` (chat completions con function calling;
  DeepSeek usa una API compatible con OpenAI).

El bucle de herramientas se ejecuta en local porque las herramientas hablan con
el adaptador conectado al coche.

Las API keys se guardan cifradas con DPAPI de Windows (solo las puede descifrar
el mismo usuario de Windows en el mismo equipo).
"""
import base64
import ctypes
import json
import os
import sys
from ctypes import wintypes

PROVEEDORES = {
    "anthropic": {
        "nombre": "Anthropic (Claude)",
        "modelo": "claude-opus-5-5",
        "url_clave": "https://platform.claude.com/settings/keys",
    },
    "openai": {
        "nombre": "OpenAI",
        "modelo": "gpt-5",
        "url_clave": "https://platform.openai.com/api-keys",
    },
    "deepseek": {
        "nombre": "DeepSeek",
        "modelo": "deepseek-chat",
        "url_clave": "https://platform.deepseek.com/api_keys",
        "base_url": "https://api.deepseek.com",
    },
}

# Modelos Claude que admiten effort + reintento automatico en otro modelo si rechazan
_CLAUDE_FALLBACK = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-2", "claude-fable-5-1",
                    "claude-sonnet-5-5"}

MAX_RONDAS = 15          # rondas de herramientas por mensaje del usuario (limita el coste)

SYSTEM_PROMPT = """Eres un técnico experto en diagnosis electrónica de automóviles, integrado en la aplicación de escritorio "Toledo Diagnosis". Puedes hacer comprobaciones en el coche tú mismo mediante herramientas.

La aplicación tiene dos modos de conexión:
- KKL · VAG KW1281: vehículos del grupo VAG hasta ~2004 con cable KKL. Identificación de la centralita, códigos de avería VAG de 5 cifras con tipo de fallo (e intermitentes) y grupos de valores medidos (en un 1.9 TDI con EDC15, por ejemplo: 001 inyección, 002 acelerador, 003 EGR/caudalímetro, 004 comienzo de inyección, 007 temperaturas, 008 limitación de caudal, 010 aire/presiones, 011 turbo, 013 marcha suave por cilindro).
- ELM327 · OBD2 genérico: cualquier coche con OBD2/EOBD. PIDs estándar, códigos P0xxx memorizados y pendientes, testigo MIL y VIN.

El vehículo principal del usuario es un SEAT Toledo II 1.9 TDI del año 2000 (centralita Bosch EDC15). Confírmalo con la identificación de la centralita; si los datos indican otro vehículo, trabaja con ese.

Diagnóstico guiado:
- Cuando el usuario describa un síntoma o pida un análisis, plantea hipótesis y comprueba las que importan con las herramientas: lee averías, lee los grupos o PIDs que confirman o descartan cada hipótesis e interpreta los valores frente a los esperados para ese motor.
- Si una lectura necesita unas condiciones concretas (motor arrancado, temperatura de servicio, un régimen fijo, un acelerón en vacío, aire acondicionado encendido…), pídeselas al usuario con pedir_accion_usuario antes de leer. Para capturar algo que dura unos segundos, primero pide la acción ("al pulsar Hecho, da un acelerón a fondo y suelta") y justo después lee con varias muestras.
- Sé eficiente: agrupa lo que puedas en una misma lectura, no repitas lecturas sin motivo y no pases de unas 10 comprobaciones salvo que de verdad haga falta.
- Si no hay conexión con el coche, pide al usuario con pedir_accion_usuario que conecte (selector «Conexión», «Puerto» y botón «Conectar» arriba) y comprueba después con estado_conexion.
- Borra averías solo si aporta al diagnóstico (ver si reaparecen) y después de haberlas leído.

Seguridad (obligatorio):
- Nunca pidas al usuario que mire la pantalla ni maneje el portátil mientras conduce. Las pruebas en circulación solo con un acompañante que maneje el portátil, en un lugar seguro y respetando las normas. Prefiere pruebas en parado.
- Avisa de los riesgos cuando pidas algo cerca del motor en marcha (correas, ventilador, partes calientes) y no pidas desconectar componentes con el motor en marcha.

Respuesta final:
- En español de España, claro y directo, para un aficionado con conocimientos de mecánica.
- Basada en los datos leídos. No inventes valores ni códigos; si algo no se pudo comprobar, dilo.
- Estructura: conclusión breve; causas más probables ordenadas por probabilidad con la evidencia que las apoya; qué hacer a continuación (de lo más barato y probable a lo más caro); si se puede circular o la urgencia.
- Recuerda cuando proceda que borrar códigos no repara la avería.
- Si analizas errores del programa o de comunicación, explica qué indica el registro (cable, puerto COM, protocolo, tiempos, contacto) y da pasos concretos.
- Formato Markdown sencillo: títulos con ##, listas con -, negritas con **. Sin tablas."""

_SIN_PARAMS = {"type": "object", "properties": {}, "additionalProperties": False}

HERRAMIENTAS = [
    {
        "name": "estado_conexion",
        "description": "Indica el modo de conexión, si hay conexión con el vehículo, los datos de la "
                       "centralita o del vehículo y qué grupos o PIDs se pueden leer.",
        "input_schema": _SIN_PARAMS,
    },
    {
        "name": "leer_averias",
        "description": "Lee los códigos de avería memorizados en la centralita conectada (en OBD2 también "
                       "los pendientes y el estado del testigo MIL). Actualiza la pestaña Averías.",
        "input_schema": _SIN_PARAMS,
    },
    {
        "name": "leer_valores",
        "description": "Lee valores medidos en directo. Modo KKL/VAG: números de grupo de valores medidos "
                       "(p. ej. \"1\", \"3\", \"11\"), máximo 4. Modo ELM327/OBD2: PIDs en hexadecimal "
                       "(p. ej. \"0C\", \"05\", \"10\"), máximo 10, solo los soportados. Con muestras > 1 "
                       "toma una serie temporal, útil durante un acelerón, un calentamiento o para ver "
                       "estabilidad. Cada lectura de un grupo VAG tarda unos 0,2-0,3 s.",
        "input_schema": {
            "type": "object",
            "properties": {
                "elementos": {"type": "array", "items": {"type": "string"},
                              "description": "Grupos VAG (decimal) o PIDs OBD2 (hexadecimal)."},
                "muestras": {"type": "integer", "description": "Número de lecturas, 1 a 40. Por defecto 1."},
                "intervalo_s": {"type": "number",
                                "description": "Segundos entre lecturas, 0 a 5. Por defecto 0 (lo más rápido posible)."},
            },
            "required": ["elementos"],
            "additionalProperties": False,
        },
    },
    {
        "name": "pedir_accion_usuario",
        "description": "Muestra al usuario una instrucción (arrancar el motor, mantener 2500 rpm, dar un "
                       "acelerón, revisar visualmente un manguito, conectar el adaptador…) y espera a que "
                       "pulse Hecho o indique que no puede. Devuelve su respuesta.",
        "input_schema": {
            "type": "object",
            "properties": {"instruccion": {"type": "string",
                                           "description": "Instrucción clara y breve, en español."}},
            "required": ["instruccion"],
            "additionalProperties": False,
        },
    },
    {
        "name": "borrar_averias",
        "description": "Borra los códigos de avería de la centralita (el usuario tiene que confirmarlo). "
                       "Devuelve las averías que siguen presentes después de borrar.",
        "input_schema": _SIN_PARAMS,
    },
    {
        "name": "leer_registro",
        "description": "Devuelve las últimas líneas del registro de la aplicación (comunicación con el "
                       "adaptador y errores).",
        "input_schema": {
            "type": "object",
            "properties": {"lineas": {"type": "integer", "description": "Número de líneas, 10 a 300. Por defecto 80."}},
            "additionalProperties": False,
        },
    },
]


class IAError(Exception):
    pass


# ---------------------------------------------------------------------------
# Configuracion (con API keys cifradas por DPAPI)
# ---------------------------------------------------------------------------
class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(data, cifrar):
    if sys.platform != "win32":
        return data
    entrada = _BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data, len(data)),
                                           ctypes.POINTER(ctypes.c_char)))
    salida = _BLOB()
    fn = ctypes.windll.crypt32.CryptProtectData if cifrar else ctypes.windll.crypt32.CryptUnprotectData
    if not fn(ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(salida)):
        raise IAError("No se pudo cifrar/descifrar la API key en este equipo.")
    try:
        return ctypes.string_at(salida.pbData, salida.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(salida.pbData)


def _ruta_config():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    carpeta = os.path.join(base, "ToledoDiagnosis")
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, "config.json")


def cargar_config():
    try:
        with open(_ruta_config(), encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {}
    cfg.setdefault("proveedor", "anthropic")
    cfg.setdefault("modelos", {})
    cfg.setdefault("claves", {})
    return cfg


def guardar_config(cfg):
    with open(_ruta_config(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def leer_clave(cfg, proveedor):
    enc = cfg["claves"].get(proveedor)
    if not enc:
        return ""
    try:
        return _dpapi(base64.b64decode(enc), cifrar=False).decode("utf-8")
    except Exception:
        return ""          # clave de otro usuario/equipo: hay que volver a introducirla


def poner_clave(cfg, proveedor, clave):
    if clave:
        cfg["claves"][proveedor] = base64.b64encode(_dpapi(clave.encode("utf-8"), cifrar=True)).decode()
    else:
        cfg["claves"].pop(proveedor, None)


def modelo_de(cfg, proveedor):
    return cfg["modelos"].get(proveedor) or PROVEEDORES[proveedor]["modelo"]


# ---------------------------------------------------------------------------
# Conversacion con herramientas
# ---------------------------------------------------------------------------
class Conversacion:
    """
    Conversacion multi-turno con un proveedor. El historial se guarda en el
    formato propio de cada proveedor, por eso cambiar de proveedor implica
    empezar una conversacion nueva.

    enviar() llama a:
      on_text(trozo)                  texto de la respuesta segun llega
      on_tool(nombre, entrada)        -> (resultado_texto, es_error); se ejecuta en este hilo
      cancelado()                     -> True para detener
    """

    def __init__(self, proveedor, api_key, modelo):
        if not api_key:
            raise IAError("Falta la API key. Introdúcela en la configuración del asistente.")
        self.proveedor = proveedor
        self.api_key = api_key
        self.modelo = modelo
        self.msgs = []

    def vacia(self):
        return not self.msgs

    def enviar(self, texto, on_text, on_tool, cancelado=lambda: False):
        inicio = len(self.msgs)
        self.msgs.append({"role": "user", "content": texto})
        try:
            if self.proveedor == "anthropic":
                ok = self._turno_claude(on_text, on_tool, cancelado)
            else:
                ok = self._turno_openai(on_text, on_tool, cancelado)
        except Exception:
            del self.msgs[inicio:]          # deja el historial coherente
            raise
        if not ok:                          # cancelado: el turno no se recuerda
            del self.msgs[inicio:]
        return ok

    # ---------------- Anthropic ----------------
    def _turno_claude(self, on_text, on_tool, cancelado):
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        tools = [dict(t, eager_input_streaming=True) for t in HERRAMIENTAS]
        hubo_texto = False
        try:
            for ronda in range(MAX_RONDAS + 1):
                kwargs = dict(model=self.modelo, max_tokens=16000, system=SYSTEM_PROMPT,
                              messages=self.msgs, tools=tools)
                if ronda == MAX_RONDAS:
                    kwargs["tool_choice"] = {"type": "none"}     # obliga a concluir
                if self.modelo in _CLAUDE_FALLBACK:
                    ctx = client.beta.messages.stream(**kwargs, output_config={"effort": "medium"},
                                                      betas=["server-side-fallback-2026-07-01"],
                                                      fallbacks="default")
                else:
                    ctx = client.messages.stream(**kwargs)
                with ctx as stream:
                    primero = True
                    for text in stream.text_stream:
                        if cancelado():
                            return False
                        if primero and hubo_texto:
                            on_text("\n\n")
                        primero = False
                        hubo_texto = True
                        on_text(text)
                    final = stream.get_final_message()

                if final.stop_reason == "refusal":
                    raise IAError("El modelo ha declinado responder a esta consulta.")
                self.msgs.append({"role": "assistant", "content": final.content})
                if final.stop_reason == "pause_turn":
                    continue
                if final.stop_reason == "max_tokens":
                    on_text("\n\n*(Respuesta cortada por longitud)*")
                    if any(b.type == "tool_use" for b in final.content):
                        self.msgs.pop()             # llamada a herramienta incompleta: no se ejecuta
                    return True
                usos = [b for b in final.content if b.type == "tool_use"]
                if final.stop_reason != "tool_use" or not usos:
                    return True
                resultados = []
                for b in usos:
                    if cancelado():
                        return False
                    res, err = self._ejecutar(on_tool, b.name, b.input, ronda)
                    resultados.append({"type": "tool_result", "tool_use_id": b.id,
                                       "content": res, "is_error": err})
                self.msgs.append({"role": "user", "content": resultados})
            return True
        except anthropic.AuthenticationError:
            raise IAError("API key de Anthropic no válida.")
        except anthropic.PermissionDeniedError:
            raise IAError("La API key no tiene permiso para usar este modelo.")
        except anthropic.NotFoundError:
            raise IAError(f"Modelo '{self.modelo}' no encontrado. Revisa el nombre del modelo.")
        except anthropic.RateLimitError:
            raise IAError("Límite de uso alcanzado o sin saldo en la cuenta. Espera o revisa la facturación.")
        except anthropic.APIConnectionError:
            raise IAError("Sin conexión con Anthropic. Comprueba la conexión a internet.")
        except anthropic.APIStatusError as e:
            raise IAError(f"Error de la API de Anthropic ({e.status_code}): {e.message}")

    # ---------------- OpenAI / DeepSeek ----------------
    def _turno_openai(self, on_text, on_tool, cancelado):
        import openai
        cfg = PROVEEDORES[self.proveedor]
        nombre = cfg["nombre"]
        client = openai.OpenAI(api_key=self.api_key, base_url=cfg.get("base_url"))
        tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                   "parameters": t["input_schema"]}} for t in HERRAMIENTAS]
        hubo_texto = False
        try:
            for ronda in range(MAX_RONDAS + 1):
                stream = client.chat.completions.create(
                    model=self.modelo, stream=True, tools=tools,
                    tool_choice="none" if ronda == MAX_RONDAS else "auto",
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.msgs)
                texto, llamadas = [], {}
                try:
                    for chunk in stream:
                        if cancelado():
                            return False
                        if not chunk.choices:
                            continue
                        d = chunk.choices[0].delta
                        if d is None:
                            continue
                        if d.content:
                            if not texto and hubo_texto:
                                on_text("\n\n")
                            texto.append(d.content)
                            hubo_texto = True
                            on_text(d.content)
                        for tc in d.tool_calls or []:
                            c = llamadas.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                            if tc.id:
                                c["id"] = tc.id
                            if tc.function:
                                c["name"] += tc.function.name or ""
                                c["args"] += tc.function.arguments or ""
                finally:
                    stream.close()
                msg = {"role": "assistant", "content": "".join(texto) or None}
                orden = [llamadas[i] for i in sorted(llamadas)]
                if orden:
                    msg["tool_calls"] = [{"id": c["id"], "type": "function",
                                          "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
                                         for c in orden]
                self.msgs.append(msg)
                if not orden:
                    return True
                for c in orden:
                    if cancelado():
                        return False
                    try:
                        entrada = json.loads(c["args"] or "{}")
                    except ValueError:
                        res, err = "Error: argumentos JSON no válidos.", True
                    else:
                        res, err = self._ejecutar(on_tool, c["name"], entrada, ronda)
                    if err:
                        res = "ERROR: " + res
                    self.msgs.append({"role": "tool", "tool_call_id": c["id"], "content": res})
            return True
        except openai.AuthenticationError:
            raise IAError(f"API key de {nombre} no válida.")
        except openai.PermissionDeniedError:
            raise IAError(f"La API key de {nombre} no tiene permiso para usar este modelo.")
        except openai.NotFoundError:
            raise IAError(f"Modelo '{self.modelo}' no encontrado en {nombre}. Revisa el nombre del modelo.")
        except openai.RateLimitError:
            raise IAError(f"Límite de uso alcanzado o sin saldo en {nombre}.")
        except openai.APIConnectionError:
            raise IAError(f"Sin conexión con {nombre}. Comprueba la conexión a internet.")
        except openai.APIStatusError as e:
            raise IAError(f"Error de la API de {nombre} ({e.status_code}): {e.message}")

    @staticmethod
    def _ejecutar(on_tool, nombre, entrada, ronda):
        if not isinstance(entrada, dict):
            return "Error: la entrada de la herramienta debe ser un objeto JSON.", True
        try:
            res, err = on_tool(nombre, entrada)
        except Exception as e:
            res, err = f"Error al ejecutar {nombre}: {e}", True
        if ronda == MAX_RONDAS - 1:
            res += ("\n\n[Límite de comprobaciones alcanzado: da ya tu conclusión con los datos "
                    "disponibles, sin usar más herramientas.]")
        return res, err
