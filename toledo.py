"""
Lector de diagnostico KW1281 para SEAT Toledo II 1.9 TDI (2000) - cable KKL FTDI.

Uso:
  python toledo.py COM3              conecta con el motor (direccion 01)
  python toledo.py COM3 --modulo 17  otro modulo (17 cuadro, 03 ABS, 15 airbag...)
  python toledo.py --sim             simulador (sin coche)
  python toledo.py COM3 --debug      muestra los bloques intercambiados

Contacto puesto. Para leer en marcha, arranca el motor despues de conectar o
antes de conectar (las dos cosas valen).
"""
import argparse
import csv
import datetime
import os
import sys
import time

from idioma import tr
from kw1281 import KW1281, KW1281Error
from vag_datos import GRUPOS_EDC15, MODULOS, decode_value, describe_dtc

CLS = "\033[H\033[J"


def abrir_puerto(args):
    if args.sim:
        from simulador import FakeSerial
        return FakeSerial()
    import serial
    ser = serial.Serial(args.puerto, 9600, timeout=0.05)
    ser.dtr = True      # alimenta la logica de algunos cables KKL
    ser.rts = False     # linea L en reposo
    if sys.platform != "win32":
        try:
            ser.set_low_latency_mode(True)   # Linux + FTDI: latencia de 16 ms a 1 ms
        except Exception:
            pass
    return ser


def texto_id(data):
    if all(32 <= c < 127 for c in data):
        return data.decode("ascii")
    imp = sum(32 <= c < 127 for c in data)
    if imp >= len(data) * 0.7:
        return "".join(chr(c) if 32 <= c < 127 else "·" for c in data)
    return "[" + data.hex(" ") + "]"


def mostrar_identificacion(ecu):
    print(f"\nMódulo {ecu.address:02X} ({MODULOS.get(ecu.address, '?')}) - "
          f"{ecu.baud} baudios, keywords {ecu.keywords[0]:02X} {ecu.keywords[1]:02X}, "
          f"eco {'sí' if ecu.echo else 'no'}")
    for i, d in enumerate(ecu.ident, 1):
        print(f"  ID {i}: {texto_id(d)}")


def mostrar_averias(ecu):
    dtcs = ecu.read_dtcs()
    if not dtcs:
        print("\nNo hay averías memorizadas.")
        return
    print(f"\n{len(dtcs)} avería(s):")
    for code, ftype, inter in dtcs:
        print("  " + describe_dtc(code, ftype, inter))


def borrar_averias(ecu):
    if input("\n¿Seguro que quieres borrar las averías? (s/N): ").strip().lower() != "s":
        print("Cancelado.")
        return
    restantes = ecu.clear_dtcs()
    if restantes:
        print("Borrado hecho, pero siguen presentes (avería activa):")
        for c in restantes:
            print("  " + describe_dtc(*c))
    else:
        print("Averías borradas.")


def leer_grupo_formateado(ecu, g, grupos=None):
    """Filas (nombre, valor, unidad, ok) del grupo g; los nombres salen de la tabla del motor."""
    campos = ecu.read_group(g)
    nombres = (GRUPOS_EDC15 if grupos is None else grupos).get(g, (None, []))[1]
    if g == 0:
        return [(tr("Byte {n}", n=i + 1), str(v), "", True) for i, v in enumerate(campos)]
    filas = []
    for i, (f, a, b) in enumerate(campos):
        valor, unidad, ok = decode_value(f, a, b)
        nombre = nombres[i] if i < len(nombres) else tr("Campo {n}", n=i + 1)
        filas.append((nombre, valor, unidad, ok))
    return filas


def pedir_grupos(texto):
    s = input(texto).strip()
    try:
        return [int(x) for x in s.replace(" ", "").split(",") if x != ""]
    except ValueError:
        print("Formato no válido. Ejemplo: 1,3,11")
        return []


def ver_grupos(ecu, grupos):
    if not grupos:
        return
    print("Leyendo... (Ctrl+C para volver al menú)")
    try:
        while True:
            salida = [f"Grupos en vivo - {datetime.datetime.now():%H:%M:%S}  (Ctrl+C para salir)\n"]
            for g in grupos:
                titulo = GRUPOS_EDC15.get(g, ("",))[0]
                salida.append(f"Grupo {g:03d} {titulo}")
                try:
                    for nombre, valor, unidad, ok in leer_grupo_formateado(ecu, g):
                        salida.append(f"   {nombre:<30} {valor:>10} {unidad}{'' if ok else '  ?'}")
                except KW1281Error as e:
                    salida.append(f"   {e}")
                    if not ecu.connected:
                        print(CLS + "\n".join(salida))
                        return
                salida.append("")
            print(CLS + "\n".join(salida), flush=True)
    except KeyboardInterrupt:
        print()


def registrar_csv(ecu, grupos):
    if not grupos:
        return
    nombre = f"log_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv"
    print(f"Registrando grupos {grupos} en {nombre} (Ctrl+C para parar)")
    cabecera_hecha = False
    n = 0
    t0 = time.monotonic()
    with open(nombre, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        try:
            while True:
                fila = [f"{time.monotonic() - t0:.2f}"]
                cab = ["t (s)"]
                for g in grupos:
                    for nombre_c, valor, unidad, _ in leer_grupo_formateado(ecu, g):
                        cab.append(f"G{g:03d} {nombre_c} ({unidad})")
                        fila.append(valor.replace(".", ","))
                if not cabecera_hecha:
                    w.writerow(cab)
                    cabecera_hecha = True
                w.writerow(fila)
                n += 1
                if n % 10 == 0:
                    fh.flush()
                    print(f"\r  {n} muestras", end="", flush=True)
        except KeyboardInterrupt:
            pass
        except KW1281Error as e:
            print(f"\nError: {e}")
    print(f"\nGuardadas {n} muestras en {os.path.abspath(nombre)}")


MENU = """
================ SEAT Toledo 1.9 TDI - KW1281 ================
 1) Identificación de la centralita
 2) Leer averías
 3) Borrar averías
 4) Valores medidos en vivo (uno o varios grupos)
 5) Registrar valores medidos a CSV
 6) Grupos típicos EDC15 (ayuda)
 0) Salir
"""


def ayuda_grupos():
    print("\nGrupos habituales en EDC15 (orientativo, puede variar según motor):")
    for g, (t, campos) in GRUPOS_EDC15.items():
        print(f"  {g:03d} {t:<26} {', '.join(campos)}")
    print("  Sugerencias: 1,3,11 (inyección, EGR/MAF, turbo)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("puerto", nargs="?", help="Puerto COM del cable KKL (p. ej. COM3)")
    ap.add_argument("--sim", action="store_true", help="Usar el simulador")
    ap.add_argument("--modulo", default="01", help="Dirección hex del módulo (01 = motor)")
    ap.add_argument("--baudios", default="10400,9600", help="Velocidades a probar")
    ap.add_argument("--retardo", type=float, default=1.0, help="Retardo entre bytes en ms")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    if not args.puerto and not args.sim:
        ap.error("Indica el puerto COM o --sim")

    os.system("")  # activa secuencias ANSI en la consola de Windows
    try:
        ser = abrir_puerto(args)
    except Exception as e:
        print(f"No se pudo abrir el puerto: {e}")
        sys.exit(1)

    ecu = KW1281(ser, address=int(args.modulo, 16),
                 bauds=tuple(int(b) for b in args.baudios.split(",")),
                 byte_delay=args.retardo / 1000, debug=args.debug)

    def conectar():
        print(f"Conectando con módulo {ecu.address:02X} "
              f"({MODULOS.get(ecu.address, '?')})... (init a 5 baudios, ~2-5 s)")
        ecu.connect()
        mostrar_identificacion(ecu)

    try:
        conectar()
    except KW1281Error as e:
        print(f"\nERROR: {e}")
        print("Revisa: contacto puesto, puerto COM correcto, cable FTDI, radio no original.")
        ser.close()
        sys.exit(1)

    try:
        while True:
            print(MENU)
            op = input("Opción: ").strip()
            if op == "0":
                break
            try:
                if not ecu.connected:
                    print(f"Conexión perdida ({ecu.error}). Reconectando...")
                    time.sleep(2.5)
                    conectar()
                if op == "1":
                    mostrar_identificacion(ecu)
                elif op == "2":
                    mostrar_averias(ecu)
                elif op == "3":
                    borrar_averias(ecu)
                elif op == "4":
                    ver_grupos(ecu, pedir_grupos("Grupo(s), separados por comas (p. ej. 1,3,11): "))
                elif op == "5":
                    registrar_csv(ecu, pedir_grupos("Grupo(s) a registrar (p. ej. 1,11): "))
                elif op == "6":
                    ayuda_grupos()
            except KW1281Error as e:
                print(f"Error: {e}")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        ecu.disconnect()
        ser.close()
        print("Comunicación cerrada.")


if __name__ == "__main__":
    main()
