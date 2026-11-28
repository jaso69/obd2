# Textos para dar a conocer OBD2Desk

Borradores para publicar a mano. Antes de cada uno:

- **Lee las normas del sitio.** Muchos foros y subreddits limitan la autopromoción: algunos tienen un hilo o un día para proyectos propios, y en otros hay que pedir permiso a los moderadores.
- **Di siempre que eres el autor.** Se agradece y evita que lo tomen por spam.
- **Un sitio cada vez, a lo largo de varios días**, y adapta el texto: el mismo mensaje copiado en diez sitios el mismo día parece spam.
- **Pon una o dos capturas** (de `web/img/`: `panel-kkl.webp`, `averias-kkl.webp`, `ia-diagnostico.webp`).
- **Contesta a los comentarios** los primeros días: las preguntas y las críticas son lo que hace que el hilo suba.

---

## 1. Foro de club VAG en español (Toledo, León, Ibiza, Golf, A3…)

Subforo de mecánica, electrónica o bricolaje.

**Título:** Programa gratuito para diagnosticar VAG antiguos con cable KKL (y OBD2 con ELM327)

> Hola a todos:
>
> Tengo un Toledo II 1.9 TDI del 2000 y, como muchos sabréis, estos coches no responden a un lector OBD2 normal: la centralita habla KW1281 por la línea K y hace falta un cable KKL. Cansado de buscar programas antiguos que solo funcionan en Windows XP, me he hecho uno, y lo comparto por si a alguien le sirve.
>
> Se llama **OBD2Desk**, es **gratis y de código abierto** (licencia MIT) y funciona en **Windows y Linux**.
>
> **Con el cable KKL (VAG hasta ~2004):**
> - Lee y borra averías de todas las centralitas (motor, ABS, airbag, cuadro, confort…) y las escanea todas de una vez.
> - Valores medidos por grupos con el nombre de cada valor (TDI de bomba rotativa, inyector-bomba y gasolina), gráficas en vivo y grabación en CSV.
> - Test de actuadores, ajustes básicos (calado de la bomba, mariposa…), canales de adaptación y codificación, con vuelta atrás.
> - Consumo del trayecto.
>
> **Con un ELM327 (cualquier coche con OBD2):** averías, datos congelados, monitores para la ITV, VIN, consumo y cronómetro 0-100.
>
> También trae un **asistente de IA opcional** que lee él mismo las averías y los valores y te va pidiendo pruebas (arrancar, acelerar…) hasta dar un diagnóstico. Necesita tu propia clave de API; el resto del programa funciona sin ella.
>
> Lo he probado en mi coche y en un par más, y trae un simulador para probarlo sin coche. He puesto también una **lista de códigos de avería VAG** con buscador (los 17xxx, los clásicos 00xxx…) y unas guías para elegir el cable KKL (que lleve chip FTDI, no CH340) y para ver qué grupos mirar en un 1.9 TDI.
>
> Web y descarga: https://www.obd2desk.com
> Códigos de avería: https://www.obd2desk.com/averias-vag/
> Código fuente: https://github.com/jaso69/obd2
>
> Si alguien lo prueba, me vendría muy bien saber con qué coche y centralita le funciona y con cuál no. Cualquier crítica o sugerencia es bienvenida.

---

## 2. Forocoches (subforo de coches)

Más corto y directo; allí se lee en diagonal.

**Título:** He hecho un programa gratis para diagnosticar el coche desde el portátil (VAG antiguos con KKL y OBD2)

> Buenas, foreros:
>
> Os dejo un programa que he hecho para diagnosticar mi Toledo 1.9 TDI del 2000, que no tiene OBD2 genérico. Es gratis, de código abierto y va en Windows y Linux.
>
> - **VAG antiguos (cable KKL de 10 €):** averías de todas las centralitas, valores medidos con gráficas, test de actuadores, ajustes básicos, adaptación y codificación.
> - **Cualquier coche con OBD2 (ELM327):** averías, datos congelados, monitores de la ITV, consumo y 0-100.
> - **Asistente de IA opcional** que lee las averías y los valores por su cuenta y te dice qué mirar.
>
> https://www.obd2desk.com
>
> También hay una lista de códigos de avería VAG con buscador: https://www.obd2desk.com/averias-vag/
>
> Se aceptan críticas, que para eso está.

---

## 3. Reddit: r/Volkswagen, r/tdi, r/GolfGTI, r/Audi, r/skoda, r/seat

Mira primero si el subreddit tiene un hilo semanal de proyectos o una etiqueta («flair») para ellos.

**Title:** I made a free, open-source diagnostic program for older VAG cars (KKL cable) and any OBD2 car

> I have a 2000 SEAT Toledo 1.9 TDI. Like most pre-2004 VAG diesels it doesn't answer a generic OBD2 reader: the ECU only speaks KW1281 over the K-line, so you need a KKL cable. Most of the free software for that only runs on old Windows, so I wrote my own, and I'm sharing it in case it helps someone.
>
> It's called **OBD2Desk**: free, open source (MIT), for **Windows and Linux**.
>
> **With a KKL cable (VAG up to ~2004):**
> - Read and clear fault codes from every module (engine, ABS, airbag, cluster, comfort…), or scan them all at once
> - Measuring blocks with named fields (TDI distributor pump, PD and petrol), live graphs and CSV logging
> - Output tests, basic settings (pump timing, throttle body…), adaptation channels and coding, with an undo log
>
> **With an ELM327 (any OBD2 car):** fault codes, freeze frame, readiness monitors, VIN, fuel consumption and a 0-100 timer.
>
> There's also an **optional AI assistant** that reads the codes and live data itself and asks you to do things (start the engine, rev it…) until it gives a diagnosis. It needs your own API key; everything else works without it.
>
> Website: https://www.obd2desk.com/en/
> VAG fault code list with search: https://www.obd2desk.com/en/vag-fault-codes/
> Source: https://github.com/jaso69/obd2
>
> It's tested on my car and a couple of others, and it has a built-in simulator so you can try it without a car. Feedback from other VAG cars and ECUs would be really useful.

---

## 4. Reddit: r/CarHacking, r/opensource, r/linux (ángulo técnico)

**Title:** OBD2Desk: open-source KW1281 + ELM327 car diagnostics in Python, for Windows and Linux

> I've been building a desktop diagnostic tool in Python/tkinter, mainly for older VAG cars that use KW1281 rather than OBD2.
>
> Some details that might interest this sub:
> - **KW1281 from scratch over a plain FTDI KKL cable:** 5-baud address wake-up using the serial break signal, baud detection (10400/9600), the per-byte complement acknowledgement and block counters. FTDI chips handle the break timing well; CH340/PL2303 generally don't.
> - **ELM327:** automatic protocol search with a fallback that forces the K-line protocols one by one (KWP2000 fast/slow init, ISO 9141) for pre-CAN cars where `ATSP0` fails, plus ISO-TP reassembly, freeze frame, readiness monitors and mode 09 (VIN, CALID/CVN).
> - **Simulators** for both adapters, so the whole protocol stack is tested without a car.
> - **Linux:** portable build that runs on Ubuntu 20.04+, Debian, Fedora, Arch and openSUSE; it sets FTDI low-latency mode automatically.
> - An **optional LLM assistant** (Claude, OpenAI or DeepSeek) that uses tool calls to read codes and live data and to ask the user for actions.
>
> MIT licensed: https://github.com/jaso69/obd2 · https://www.obd2desk.com/en/
>
> Happy to answer questions about the protocol side.

---

## 5. Foros en inglés: TDIClub, VWVortex

Usa el texto de Reddit (apartado 3) con estos cambios:
- **TDIClub**: subforo del motor de tu coche o de «VCDS / diagnostics». Empieza por el 1.9 TDI y enlaza la guía de grupos: https://www.obd2desk.com/en/guides/1-9-tdi-measuring-blocks/
- **VWVortex**: subforo del modelo (Mk4 Golf/Jetta, etc.) o de electrónica.
- No lo publiques en los foros de Ross-Tech: venden VCDS y sería promocionar la competencia en su casa.

---

## 6. AlternativeTo (https://alternativeto.net)

Botón «Suggest an application». Campos:

- **Name:** OBD2Desk
- **Website:** https://www.obd2desk.com/en/
- **Short description:** Free, open-source car diagnostics for Windows and Linux: older VAG cars with a KKL cable (KW1281) and any OBD2 car with an ELM327, with an optional AI assistant.
- **Description:**
  > OBD2Desk is a desktop program to diagnose cars from a laptop. With a cheap KKL cable it talks KW1281 to pre-2004 Volkswagen, Audi, SEAT and Skoda cars: fault codes from every module, module scan, measuring blocks with live graphs and CSV logging, output tests, basic settings, adaptation and coding. With an ELM327 (USB, Bluetooth or WiFi) it works with any OBD2 car: fault codes, freeze frame, readiness monitors, VIN decoding, fuel consumption and a 0-100 timer. An optional AI assistant (Claude, OpenAI or DeepSeek, with your own API key) reads the data itself and guides the diagnosis. It keeps a history per car, generates printable reports and includes simulators to try it without a car. Available in English and Spanish.
- **License:** Open Source (MIT) · **Price:** Free
- **Platforms:** Windows, Linux
- **Tags:** obd2, car-diagnostics, vag, elm327, kw1281, automotive
- **Alternative to:** VCDS, VCDS-Lite, OBDeleven, Torque, Car Scanner ELM OBD2, ScanMaster-ELM
- **Logo:** `web/img/icono.png` · **Capturas:** `web/img/en/panel-kkl.webp`, `web/img/en/averias-kkl.webp`, `web/img/en/ia-diagnostico.webp`
