"""
Guías de la web (español e inglés). Las genera generar_paginas.py en /guias/ y /en/guides/.
Cada guía: slugs, título de pestaña, descripción, h1 y cuerpo HTML en cada idioma.
Las tablas de grupos del 1.9 TDI salen de vag_datos.py (las rellena generar_paginas.py en {GRUPOS_*}).
No se publica.
"""

GUIAS = [
    dict(
        slug_es="cable-kkl", slug_en="kkl-cable",
        corto_es="Cable KKL 409.1", corto_en="KKL 409.1 cable",
        title_es="Cable KKL 409.1 para VAG: cómo elegir uno que funcione (FTDI o CH340) · OBD2Desk",
        title_en="KKL 409.1 cable for VAG: how to choose one that works (FTDI or CH340) · OBD2Desk",
        desc_es="Qué cable KKL VAG-COM 409.1 comprar para diagnosticar SEAT, VW, Audi y Skoda anteriores a 2004 (KW1281): chip FTDI o CH340, cómo comprobarlo, interruptor de 4 posiciones y qué hacer si no conecta.",
        desc_en="Which KKL VAG-COM 409.1 cable to buy to diagnose pre-2004 VW, Audi, SEAT and Skoda cars (KW1281): FTDI or CH340 chip, how to check it, 4-position switch and what to do if it does not connect.",
        h1_es="Cable KKL 409.1 para VAG: cómo elegir uno que funcione",
        h1_en="KKL 409.1 cable for VAG: how to choose one that works",
        resumen_es="Qué chip debe llevar, cómo comprobarlo y qué hacer si no conecta.",
        resumen_en="Which chip it needs, how to check it and what to do if it does not connect.",
        es="""
<p class="intro">Para diagnosticar un SEAT, Volkswagen, Audi o Skoda de antes de ~2004 hace falta un <strong>cable KKL</strong> (también llamado «VAG-COM 409.1»). Es un adaptador USB barato, de unos 10-20 €, pero no todos funcionan: lo que importa es el chip que llevan dentro.</p>

<h2>Para qué sirve y por qué no vale un ELM327</h2>
<p>Los VAG antiguos hablan <strong>KW1281</strong>, el protocolo propio del grupo, por la <strong>línea K</strong> (pin 7 del conector de diagnóstico). Es muy distinto del OBD2: el ordenador tiene que despertar la centralita enviando su dirección a 5 baudios y, después, confirmar cada byte que recibe devolviendo su complemento, con tiempos de unos pocos milisegundos.</p>
<p>Un <strong>ELM327</strong> no puede hacer esa confirmación byte a byte, así que no sirve para KW1281. El cable KKL, en cambio, solo convierte la línea K en un puerto serie y deja que el programa haga todo el protocolo. Por eso con él se entra en <strong>todas las centralitas</strong>: motor, cambio, ABS, airbag, cuadro, confort, radio…</p>

<h2>¿Lo necesito?</h2>
<ul class="lista-ok">
<li>Si tu VAG es <strong>anterior a 2004</strong>, sobre todo si es <strong>diésel</strong>: en Europa el EOBD fue obligatorio en gasolina desde 2001 y en diésel desde 2003-2004. Un 1.9 TDI del año 2000 tiene el conector de 16 pines, pero normalmente no responde a un lector OBD2.</li>
<li>Si un ELM327 te dice que «el vehículo no responde a OBD2» con el contacto puesto.</li>
<li>Si quieres entrar en centralitas que el OBD2 no ve (ABS, airbag, cuadro, confort) o hacer test de actuadores, ajustes básicos, adaptación o codificación.</li>
</ul>

<h2>El chip es lo que importa: FTDI sí, CH340 no</h2>
<p>El arranque a 5 baudios exige controlar con precisión la señal <em>break</em> del puerto serie. Los chips <strong>FTDI FT232RL o FT232RQ</strong> lo hacen bien; los <strong>CH340/CH341</strong> y los <strong>PL2303</strong>, no: el cable aparece en el sistema, pero la centralita no contesta.</p>
<p>Cómo saber qué chip lleva el tuyo:</p>
<ul class="lista-ok">
<li><strong>Windows</strong>: <em>Administrador de dispositivos → Puertos (COM y LPT) → el puerto del cable → Propiedades → Detalles → Id. de hardware</em>. <code>VID_0403&amp;PID_6001</code> es FTDI; <code>VID_1A86</code> es CH340; <code>VID_067B</code> es PL2303.</li>
<li><strong>Linux</strong>: ejecuta <code>lsusb</code> con el cable enchufado. <code>0403:6001 Future Technology Devices</code> es FTDI; <code>1a86:7523</code> es CH340.</li>
</ul>
<p>Al comprar, busca «KKL 409.1 FTDI» o «FT232RL» en la descripción, y desconfía de los que no dicen el chip.</p>

<h2>FTDI falsos</h2>
<p>Muchos cables baratos llevan chips FTDI falsificados. Algunos drivers oficiales los detectan y los dejan inservibles: el puerto aparece, pero no comunica. Suele arreglarse instalando un driver de FTDI anterior. Si puedes, compra en una tienda que acepte devoluciones.</p>

<h2>Cables con interruptor de 4 posiciones</h2>
<p>Los cables «KKL 409.1 + Fiat ECU Scan» traen un interruptor de 4 posiciones que cambia a qué pines del conector va la línea K. Valen para VAG en la <strong>posición 1</strong> (línea K al pin 7). Si no responde, prueba las demás.</p>

<h2>Lo que no sirve</h2>
<ul class="lista-no">
<li>Los <strong>ELM327 con interruptor HS-CAN/MS-CAN</strong>: son para Ford (FORScan); su chip USB va al ELM327, no a la línea K.</li>
<li>El <strong>«VAG K+CAN Commander»</strong>: está pensado para inmovilizador y llaves, y su parte de línea K no está garantizada. No lo recomendamos.</li>
<li>No existe un cable KKL inalámbrico de serie: Bluetooth y WiFi añaden demasiado retraso para los tiempos del KW1281.</li>
</ul>

<h2>Configurarlo</h2>
<ul class="lista-ok">
<li><strong>Windows</strong>: el driver lo instala Windows Update. Pon la latencia a 1 ms en <em>Administrador de dispositivos → Puertos → USB Serial Port → Propiedades → Configuración de puerto → Opciones avanzadas → Temporizador de latencia</em>. Evita que la sesión se corte. Hay que hacerlo en cada ordenador.</li>
<li><strong>Linux</strong>: no hace falta driver y OBD2Desk ajusta la latencia solo. Tu usuario debe estar en el grupo del puerto: <code>sudo usermod -aG dialout $USER</code> (en Arch, <code>uucp</code>) y volver a iniciar sesión. En Ubuntu y Mint, si el cable no aparece como <code>/dev/ttyUSB0</code>, quita el lector braille: <code>sudo apt remove brltty</code>.</li>
</ul>

<h2>Si no conecta</h2>
<ul class="lista-ok">
<li><strong>Contacto puesto</strong> (para leer averías basta con el motor parado) y el puerto correcto elegido en el programa.</li>
<li><strong>«Sin byte de sincronismo 0x55»</strong>: la centralita no ha contestado. Revisa el chip, el interruptor y el driver. Una <strong>radio no original</strong> puede bloquear la línea K: desconéctala para probar.</li>
<li><strong>«Keywords KWP2000»</strong>: esa centralita no habla KW1281 sino KWP2000, más moderno. Usa un ELM327 en modo OBD2.</li>
<li>Prueba antes el programa con el puerto «Simulador (sin coche)» para descartar que el problema sea del ordenador.</li>
</ul>
""",
        en="""
<p class="intro">To diagnose a Volkswagen, Audi, SEAT or Skoda from before ~2004 you need a <strong>KKL cable</strong> (also sold as “VAG-COM 409.1”). It is a cheap USB adapter, about €10-20, but not all of them work: what matters is the chip inside.</p>

<h2>What it is for and why an ELM327 will not do</h2>
<p>Older VAG cars speak <strong>KW1281</strong>, the group's own protocol, over the <strong>K-line</strong> (pin 7 of the diagnostic connector). It is very different from OBD2: the computer has to wake the control unit by sending its address at 5 baud and then acknowledge every byte it receives by sending back its complement, with timings of a few milliseconds.</p>
<p>An <strong>ELM327</strong> cannot do that byte-by-byte acknowledgement, so it does not work for KW1281. A KKL cable, on the other hand, just turns the K-line into a serial port and lets the program handle the whole protocol. That is why it reaches <strong>every control unit</strong>: engine, transmission, ABS, airbag, cluster, convenience, radio…</p>

<h2>Do I need one?</h2>
<ul class="lista-ok">
<li>If your VAG car is <strong>older than 2004</strong>, especially a <strong>diesel</strong>: in Europe EOBD became mandatory for petrol cars in 2001 and for diesels in 2003-2004. A 2000 1.9 TDI has the 16-pin connector but usually does not answer an OBD2 reader.</li>
<li>If an ELM327 tells you that “the vehicle does not respond to OBD2” with the ignition on.</li>
<li>If you want to reach control units OBD2 cannot see (ABS, airbag, cluster, convenience) or run output tests, basic settings, adaptation or coding.</li>
</ul>

<h2>The chip is what matters: FTDI yes, CH340 no</h2>
<p>The 5-baud wake-up needs precise control of the serial port's <em>break</em> signal. <strong>FTDI FT232RL or FT232RQ</strong> chips do it well; <strong>CH340/CH341</strong> and <strong>PL2303</strong> chips do not: the cable shows up in the system, but the control unit never answers.</p>
<p>How to tell which chip yours has:</p>
<ul class="lista-ok">
<li><strong>Windows</strong>: <em>Device Manager → Ports (COM &amp; LPT) → the cable's port → Properties → Details → Hardware Ids</em>. <code>VID_0403&amp;PID_6001</code> is FTDI; <code>VID_1A86</code> is CH340; <code>VID_067B</code> is PL2303.</li>
<li><strong>Linux</strong>: run <code>lsusb</code> with the cable plugged in. <code>0403:6001 Future Technology Devices</code> is FTDI; <code>1a86:7523</code> is CH340.</li>
</ul>
<p>When buying, look for “KKL 409.1 FTDI” or “FT232RL” in the listing, and be wary of the ones that do not name the chip.</p>

<h2>Fake FTDI chips</h2>
<p>Many cheap cables carry counterfeit FTDI chips. Some official drivers detect them and make them useless: the port appears but does not communicate. Installing an older FTDI driver usually fixes it. If you can, buy from a shop that accepts returns.</p>

<h2>Cables with a 4-position switch</h2>
<p>“KKL 409.1 + Fiat ECU Scan” cables have a 4-position switch that changes which connector pins the K-line goes to. They work for VAG in <strong>position 1</strong> (K-line to pin 7). If it does not answer, try the others.</p>

<h2>What does not work</h2>
<ul class="lista-no">
<li><strong>ELM327 adapters with an HS-CAN/MS-CAN switch</strong>: they are for Ford (FORScan); their USB chip goes to the ELM327, not to the K-line.</li>
<li>The <strong>“VAG K+CAN Commander”</strong>: it is meant for immobilizers and keys, and its K-line side is not guaranteed. We do not recommend it.</li>
<li>There is no off-the-shelf wireless KKL cable: Bluetooth and WiFi add too much delay for KW1281 timings.</li>
</ul>

<h2>Setting it up</h2>
<ul class="lista-ok">
<li><strong>Windows</strong>: Windows Update installs the driver. Set the latency to 1 ms in <em>Device Manager → Ports → USB Serial Port → Properties → Port Settings → Advanced → Latency Timer</em>. It stops the session from dropping. It has to be done on each computer.</li>
<li><strong>Linux</strong>: no driver needed, and OBD2Desk sets the latency itself. Your user must be in the port's group: <code>sudo usermod -aG dialout $USER</code> (on Arch, <code>uucp</code>) and log in again. On Ubuntu and Mint, if the cable does not show up as <code>/dev/ttyUSB0</code>, remove the braille driver: <code>sudo apt remove brltty</code>.</li>
</ul>

<h2>If it does not connect</h2>
<ul class="lista-ok">
<li><strong>Ignition on</strong> (the engine can be off to read fault codes) and the right port selected in the program.</li>
<li><strong>“No 0x55 sync byte”</strong>: the control unit did not answer. Check the chip, the switch and the driver. An <strong>aftermarket radio</strong> can block the K-line: disconnect it to test.</li>
<li><strong>“KWP2000 keywords”</strong>: that control unit speaks the newer KWP2000 rather than KW1281. Use an ELM327 in OBD2 mode.</li>
<li>Try the program first with the “Simulator (no car)” port to rule out a problem on the computer.</li>
</ul>
""",
    ),
    dict(
        slug_es="elm327-bluetooth-wifi", slug_en="elm327-bluetooth-wifi",
        corto_es="ELM327 Bluetooth y WiFi", corto_en="ELM327 Bluetooth and WiFi",
        title_es="Conectar un ELM327 Bluetooth o WiFi al portátil (Windows y Linux) · OBD2Desk",
        title_en="Connect a Bluetooth or WiFi ELM327 to your laptop (Windows and Linux) · OBD2Desk",
        desc_es="Paso a paso para conectar un adaptador OBD2 ELM327 Bluetooth o WiFi a un portátil con Windows 10/11 o Linux: emparejar, encontrar el puerto COM o /dev/rfcomm0 y solucionar problemas.",
        desc_en="Step by step to connect a Bluetooth or WiFi ELM327 OBD2 adapter to a Windows 10/11 or Linux laptop: pairing, finding the COM port or /dev/rfcomm0, and troubleshooting.",
        h1_es="Conectar un ELM327 Bluetooth o WiFi al portátil",
        h1_en="Connect a Bluetooth or WiFi ELM327 to your laptop",
        resumen_es="Emparejar, encontrar su puerto en Windows y Linux, y qué hacer si no responde.",
        resumen_en="Pairing, finding its port on Windows and Linux, and what to do if it does not answer.",
        es="""
<p class="intro">Un ELM327 es el adaptador OBD2 más barato y común: sirve para cualquier coche con OBD2/EOBD (en Europa, gasolina desde 2001 y diésel desde 2003-2004). Los hay USB, Bluetooth y WiFi. Esta guía explica cómo conectarlos a un portátil.</p>

<h2>Cómo funciona: un puerto serie sin cable</h2>
<p>Un ELM327 Bluetooth se comporta como un <strong>cable serie sin cable</strong>. Al emparejarlo, el sistema crea un <strong>puerto serie virtual</strong>: un puerto COM en Windows o <code>/dev/rfcomm0</code> en Linux. El programa habla con ese puerto igual que con un adaptador USB. Por eso en un programa de diagnóstico no se elige «el Bluetooth», sino <strong>ese puerto</strong>.</p>
<p>Un ELM327 WiFi crea su propia red; el portátil se conecta a ella y el programa habla con el adaptador por una dirección IP y un puerto, casi siempre <code>192.168.0.10:35000</code>.</p>

<h2>Qué tipo comprar</h2>
<ul class="lista-ok">
<li><strong>USB</strong>: el más fiable y el más rápido. Aparece directamente como puerto COM o <code>/dev/ttyUSB0</code>.</li>
<li><strong>Bluetooth clásico</strong> (SPP): cómodo y funciona bien en Windows y Linux.</li>
<li><strong>WiFi</strong>: funciona, pero mientras estás conectado a su red el portátil se queda sin internet.</li>
</ul>
<ul class="lista-no">
<li>Los <strong>solo BLE</strong> (Bluetooth de bajo consumo, algunos vendidos para iPhone) no crean puerto serie en el ordenador.</li>
<li>Muchos clones dicen «v2.1» y son versiones antiguas incompletas. Suelen funcionar, pero alguno falla con ciertos coches.</li>
</ul>

<h2>Windows 10 y 11</h2>
<ol class="lista-pasos">
<li>Enchufa el ELM327 al conector OBD y pon el contacto: se enciende su luz.</li>
<li>Ve a <em>Configuración → Bluetooth y dispositivos → Agregar dispositivo → Bluetooth</em> y elige el adaptador. Suele llamarse <strong>OBDII</strong>, <strong>OBD2</strong> o <strong>V-LINK</strong>. Si pide PIN, prueba <code>1234</code>, <code>0000</code> o <code>6789</code>.</li>
<li>Mira qué puerto le ha dado: <em>Más opciones de Bluetooth → pestaña Puertos COM</em>, el de dirección <strong>Saliente</strong> (por ejemplo, COM5). También aparece en <em>Administrador de dispositivos → Puertos (COM y LPT)</em> como «Vínculo serie estándar a través de Bluetooth».</li>
<li>En el programa, elige ese puerto y pulsa Conectar.</li>
</ol>
<p>Es normal que Windows lo muestre como «Emparejado» y no como «Conectado»: la conexión se abre cuando el programa abre el puerto. Windows suele crear <strong>dos puertos COM</strong>; si uno no responde, prueba el otro.</p>

<h2>Linux</h2>
<ol class="lista-pasos">
<li>Enchufa el ELM327 y pon el contacto.</li>
<li>Empareja desde los ajustes de Bluetooth del escritorio o en un terminal con <code>bluetoothctl</code>: <code>scan on</code>, y cuando aparezca, <code>pair AA:BB:CC:DD:EE:FF</code> y <code>trust AA:BB:CC:DD:EE:FF</code> (la MAC es la que sale al buscar).</li>
<li>Linux no crea el puerto serie solo. Créalo con <code>sudo rfcomm bind 0 AA:BB:CC:DD:EE:FF</code> y tendrás <code>/dev/rfcomm0</code>. Hay que repetirlo después de reiniciar.</li>
<li>Tu usuario necesita permiso para usar puertos serie: <code>sudo usermod -aG dialout $USER</code> (en Arch, <code>uucp</code>) y volver a iniciar sesión.</li>
<li>En el programa, elige <code>/dev/rfcomm0</code> y pulsa Conectar.</li>
</ol>
<p>Si no tienes el comando <code>rfcomm</code>: en Fedora está en el paquete <code>bluez-deprecated</code>; en Arch, en <code>bluez-deprecated-tools</code>. En Debian, Ubuntu y Mint ya viene con <code>bluez</code>.</p>

<h2>ELM327 WiFi</h2>
<ol class="lista-pasos">
<li>Enchufa el adaptador y pon el contacto. Crea una red WiFi llamada, por ejemplo, «WiFi_OBDII», «OBDII» o «V-LINK».</li>
<li>Conecta el portátil a esa red.</li>
<li>En OBD2Desk, elige el puerto «WiFi · 192.168.0.10:35000». Si tu adaptador usa otra dirección (por ejemplo, 192.168.1.10), escríbela con el formato <code>ip:puerto</code>.</li>
</ol>
<p>Mientras estés en la red del adaptador no tendrás internet, así que el asistente de IA no funcionará a la vez.</p>

<h2>Si no responde</h2>
<ul class="lista-ok">
<li><strong>Solo admite una conexión a la vez.</strong> Si lo has usado con el móvil (Torque, Car Scanner…), cierra esa app o apaga el Bluetooth del móvil.</li>
<li><strong>«El vehículo no responde a OBD2»</strong>: pon el contacto. Si es un VAG anterior a 2004, probablemente no tenga OBD2 genérico y necesites un <a href="{guia:cable-kkl}">cable KKL</a>.</li>
<li><strong>Coches anteriores a CAN</strong> (hasta ~2005-2007): hablan OBD2 por la línea K y la búsqueda automática del ELM327 a veces falla. OBD2Desk prueba después KWP2000 e ISO 9141 uno a uno; tarda hasta un minuto.</li>
<li>Si nada funciona, el adaptador puede ser un clon que no maneja bien la línea K. Con uno USB de calidad se descarta.</li>
</ul>
""",
        en="""
<p class="intro">An ELM327 is the cheapest and most common OBD2 adapter: it works with any car with OBD2/EOBD (in Europe, petrol cars from 2001 and diesels from 2003-2004). They come as USB, Bluetooth and WiFi. This guide explains how to connect them to a laptop.</p>

<h2>How it works: a serial port without the cable</h2>
<p>A Bluetooth ELM327 behaves like a <strong>serial cable without the cable</strong>. When you pair it, the system creates a <strong>virtual serial port</strong>: a COM port on Windows or <code>/dev/rfcomm0</code> on Linux. The program talks to that port just as it would to a USB adapter. That is why in a diagnostic program you do not choose “Bluetooth” but <strong>that port</strong>.</p>
<p>A WiFi ELM327 creates its own network; the laptop joins it and the program talks to the adapter at an IP address and port, nearly always <code>192.168.0.10:35000</code>.</p>

<h2>Which type to buy</h2>
<ul class="lista-ok">
<li><strong>USB</strong>: the most reliable and fastest. It shows up straight away as a COM port or <code>/dev/ttyUSB0</code>.</li>
<li><strong>Classic Bluetooth</strong> (SPP): convenient and works well on Windows and Linux.</li>
<li><strong>WiFi</strong>: works, but while you are on its network the laptop has no internet.</li>
</ul>
<ul class="lista-no">
<li><strong>BLE-only</strong> adapters (Bluetooth Low Energy, some sold for iPhone) do not create a serial port on a computer.</li>
<li>Many clones claim “v2.1” and are old, incomplete versions. They usually work, but some fail with certain cars.</li>
</ul>

<h2>Windows 10 and 11</h2>
<ol class="lista-pasos">
<li>Plug the ELM327 into the OBD connector and switch the ignition on: its light comes on.</li>
<li>Go to <em>Settings → Bluetooth &amp; devices → Add device → Bluetooth</em> and choose the adapter. It is usually called <strong>OBDII</strong>, <strong>OBD2</strong> or <strong>V-LINK</strong>. If it asks for a PIN, try <code>1234</code>, <code>0000</code> or <code>6789</code>.</li>
<li>Check which port it got: <em>More Bluetooth settings → COM Ports tab</em>, the <strong>Outgoing</strong> one (for example, COM5). It also appears in <em>Device Manager → Ports (COM &amp; LPT)</em> as “Standard Serial over Bluetooth link”.</li>
<li>In the program, choose that port and click Connect.</li>
</ol>
<p>It is normal for Windows to show it as “Paired” rather than “Connected”: the connection opens when the program opens the port. Windows usually creates <strong>two COM ports</strong>; if one does not answer, try the other.</p>

<h2>Linux</h2>
<ol class="lista-pasos">
<li>Plug the ELM327 in and switch the ignition on.</li>
<li>Pair it from your desktop's Bluetooth settings or in a terminal with <code>bluetoothctl</code>: <code>scan on</code>, and when it appears, <code>pair AA:BB:CC:DD:EE:FF</code> and <code>trust AA:BB:CC:DD:EE:FF</code> (the MAC is the one shown while scanning).</li>
<li>Linux does not create the serial port by itself. Create it with <code>sudo rfcomm bind 0 AA:BB:CC:DD:EE:FF</code> and you get <code>/dev/rfcomm0</code>. Repeat it after a reboot.</li>
<li>Your user needs permission to use serial ports: <code>sudo usermod -aG dialout $USER</code> (on Arch, <code>uucp</code>) and log in again.</li>
<li>In the program, choose <code>/dev/rfcomm0</code> and click Connect.</li>
</ol>
<p>If you do not have the <code>rfcomm</code> command: on Fedora it is in the <code>bluez-deprecated</code> package; on Arch, in <code>bluez-deprecated-tools</code>. On Debian, Ubuntu and Mint it comes with <code>bluez</code>.</p>

<h2>WiFi ELM327</h2>
<ol class="lista-pasos">
<li>Plug the adapter in and switch the ignition on. It creates a WiFi network called, for example, “WiFi_OBDII”, “OBDII” or “V-LINK”.</li>
<li>Connect the laptop to that network.</li>
<li>In OBD2Desk, choose the “WiFi · 192.168.0.10:35000” port. If your adapter uses another address (for example, 192.168.1.10), type it as <code>ip:port</code>.</li>
</ol>
<p>While you are on the adapter's network you have no internet, so the AI assistant will not work at the same time.</p>

<h2>If it does not answer</h2>
<ul class="lista-ok">
<li><strong>It only accepts one connection at a time.</strong> If you have used it with your phone (Torque, Car Scanner…), close that app or turn the phone's Bluetooth off.</li>
<li><strong>“The vehicle does not respond to OBD2”</strong>: switch the ignition on. If it is a VAG car from before 2004, it probably has no generic OBD2 and you need a <a href="{guia:cable-kkl}">KKL cable</a>.</li>
<li><strong>Pre-CAN cars</strong> (up to ~2005-2007): they speak OBD2 over the K-line and the ELM327's automatic search sometimes fails. OBD2Desk then tries KWP2000 and ISO 9141 one by one; it takes up to a minute.</li>
<li>If nothing works, the adapter may be a clone that does not handle the K-line well. A good-quality USB one rules that out.</li>
</ul>
""",
    ),
    dict(
        slug_es="grupos-1-9-tdi", slug_en="1-9-tdi-measuring-blocks",
        corto_es="Valores medidos del 1.9 TDI", corto_en="1.9 TDI measuring blocks",
        title_es="Valores medidos del 1.9 TDI: qué grupos mirar (EDC15 e inyector-bomba) · OBD2Desk",
        title_en="1.9 TDI measuring blocks: which groups to check (EDC15 and PD) · OBD2Desk",
        desc_es="Qué muestra cada grupo de valores medidos del 1.9 TDI de bomba rotativa (Bosch EDC15V) e inyector-bomba, y cuáles mirar según el síntoma: falta de potencia, humo negro, tirones o arranque difícil.",
        desc_en="What each measuring block of the 1.9 TDI with distributor pump (Bosch EDC15V) and unit injectors (PD) shows, and which to check for each symptom: lack of power, black smoke, hesitation or hard starting.",
        h1_es="Valores medidos del 1.9 TDI: qué grupos mirar",
        h1_en="1.9 TDI measuring blocks: which groups to check",
        resumen_es="Qué muestra cada grupo de la EDC15 y del inyector-bomba, y cuáles mirar según el síntoma.",
        resumen_en="What each EDC15 and unit-injector group shows, and which to check for each symptom.",
        es="""
<p class="intro">La centralita de un 1.9 TDI da sus datos en <strong>grupos de valores medidos</strong>: cada grupo es un número de 3 cifras con cuatro casillas. Saber qué grupo mirar ahorra mucho tiempo: muchas averías se ven comparando un valor <strong>teórico</strong> (lo que la centralita pide) con el <strong>real</strong> (lo que mide).</p>

<h2>Bomba rotativa o inyector-bomba</h2>
<p>Lo que significa cada casilla depende del motor:</p>
<ul class="lista-ok">
<li><strong>Bomba rotativa</strong> con centralita <strong>Bosch EDC15V</strong>: los 1.9 TDI de 90 y 110 CV de finales de los 90 y principios de los 2000 (por ejemplo, ALH, AGR, AHF y ASV).</li>
<li><strong>Inyector-bomba</strong> (PD, «Pumpe-Düse»), con EDC15P o EDC16: los TDI posteriores, como el ARL de 150 CV. En lugar de una bomba hay un inyector-bomba por cilindro.</li>
</ul>
<p>OBD2Desk reconoce el motor por la identificación de la centralita y elige solo los nombres correctos. Los nombres son orientativos y pueden variar según la versión; las unidades las calcula el programa con la fórmula que envía la propia centralita.</p>

<h2>Grupos del TDI de bomba rotativa (EDC15V)</h2>
{GRUPOS_EDC15}

<h2>Grupos del TDI inyector-bomba (PD)</h2>
{GRUPOS_PD}

<h2>Qué grupos mirar según el síntoma</h2>
<h3>Falta de potencia o modo de emergencia</h3>
<ul class="lista-ok">
<li><strong>011 · turbo</strong>: compara la presión de sobrealimentación teórica con la real en plena carga. Si la real no llega a la teórica, busca fugas en los manguitos, la válvula N75 o el varillaje del turbo; si se pasa, el turbo puede estar agarrotado. El ciclo de la N75 dice cuánto está intentando corregir la centralita.</li>
<li><strong>003 · masa de aire</strong>: si la real queda muy por debajo de la teórica con la EGR cerrada (al acelerar), el caudalímetro puede estar mal.</li>
<li><strong>008 · limitación de caudal</strong>: dice si la centralita está recortando el gasóleo y por qué (por régimen, por masa de aire o, en los PD, por humos).</li>
</ul>
<h3>Humo negro</h3>
<ul class="lista-ok">
<li><strong>003</strong>: demasiado poco aire para el gasóleo inyectado. Una EGR que se queda abierta o un caudalímetro que mide de menos dan humo.</li>
<li><strong>011</strong>: si el turbo no da presión, también falta aire.</li>
</ul>
<h3>Tirones, ralentí irregular o vibraciones</h3>
<ul class="lista-ok">
<li><strong>013 · marcha suave</strong>: la corrección de caudal de cada cilindro al ralentí. Un cilindro con una desviación mucho mayor que los demás apunta a ese inyector.</li>
<li>En los PD, <strong>018</strong> y <strong>023</strong> muestran el estado y la conmutación de cada inyector-bomba.</li>
</ul>
<h3>Arranque difícil o ruido de inyección</h3>
<ul class="lista-ok">
<li><strong>004 · comienzo de inyección</strong> (bomba rotativa): compara el teórico con el real. Si se separan mucho, puede faltar el calado de la bomba, que se hace en ajustes básicos.</li>
<li><strong>001</strong> y <strong>007</strong>: temperaturas del refrigerante y del combustible. Un transmisor que marca de más o de menos hace que la centralita calcule mal la inyección en frío.</li>
</ul>

<h2>Cómo leerlos con OBD2Desk</h2>
<ol class="lista-pasos">
<li>Conecta con un <a href="{guia:cable-kkl}">cable KKL</a>, contacto puesto o motor en marcha.</li>
<li>En <em>Valores medidos</em>, comprueba el tipo de motor en <em>Motor</em> y marca los grupos que quieras.</li>
<li>Haz clic en una fila para verla en la <strong>gráfica en vivo</strong>; con Ctrl+clic comparas hasta cuatro, por ejemplo la presión de turbo teórica y la real.</li>
<li>Pulsa <strong>Grabar CSV</strong> para guardar una prueba y analizarla después en el visor. Las pruebas en marcha, siempre con un acompañante que maneje el portátil y donde se pueda hacer con seguridad.</li>
</ol>
<p>Si algo no cuadra, el asistente de IA del programa puede leer estos grupos por su cuenta y decirte qué mirar.</p>
""",
        en="""
<p class="intro">A 1.9 TDI control unit gives its data in <strong>measuring blocks</strong> (groups): each group is a 3-digit number with four fields. Knowing which group to check saves a lot of time: many faults show up by comparing a <strong>specified</strong> value (what the control unit asks for) with the <strong>actual</strong> one (what it measures).</p>

<h2>Distributor pump or unit injector</h2>
<p>What each field means depends on the engine:</p>
<ul class="lista-ok">
<li><strong>Distributor pump</strong> with a <strong>Bosch EDC15V</strong> control unit: the 90 and 110 hp 1.9 TDIs of the late 90s and early 2000s (for example ALH, AGR, AHF and ASV).</li>
<li><strong>Unit injector</strong> (PD, “Pumpe-Düse”), with EDC15P or EDC16: later TDIs such as the 150 hp ARL. Instead of one pump there is a unit injector per cylinder.</li>
</ul>
<p>OBD2Desk recognises the engine from the control unit identification and picks the right names itself. The names are for guidance and can vary between versions; the program works out the units with the formula the control unit itself sends.</p>

<h2>TDI distributor pump groups (EDC15V)</h2>
{GRUPOS_EDC15}

<h2>TDI unit injector groups (PD)</h2>
{GRUPOS_PD}

<h2>Which groups to check for each symptom</h2>
<h3>Lack of power or limp mode</h3>
<ul class="lista-ok">
<li><strong>011 · turbo</strong>: compare specified and actual boost pressure at full load. If the actual pressure does not reach the specified one, look for leaking hoses, the N75 valve or the turbo linkage; if it overshoots, the turbo may be sticking. The N75 duty cycle tells you how hard the control unit is trying to correct it.</li>
<li><strong>003 · air mass</strong>: if the actual air mass stays well below the specified one with the EGR closed (when accelerating), the MAF sensor may be faulty.</li>
<li><strong>008 · fuel quantity limitation</strong>: tells you whether the control unit is cutting fuel and why (engine speed, air mass or, on PD engines, smoke).</li>
</ul>
<h3>Black smoke</h3>
<ul class="lista-ok">
<li><strong>003</strong>: too little air for the injected fuel. An EGR valve stuck open or a MAF sensor reading low causes smoke.</li>
<li><strong>011</strong>: if the turbo does not build boost, air is short as well.</li>
</ul>
<h3>Hesitation, rough idle or vibration</h3>
<ul class="lista-ok">
<li><strong>013 · smooth running</strong>: the fuel correction for each cylinder at idle. One cylinder with a much larger deviation than the others points to that injector.</li>
<li>On PD engines, <strong>018</strong> and <strong>023</strong> show the status and switching of each unit injector.</li>
</ul>
<h3>Hard starting or injection noise</h3>
<ul class="lista-ok">
<li><strong>004 · start of injection</strong> (distributor pump): compare specified and actual. If they are far apart, the pump timing may need setting, which is done in basic settings.</li>
<li><strong>001</strong> and <strong>007</strong>: coolant and fuel temperatures. A sender that reads too high or too low makes the control unit get cold-start injection wrong.</li>
</ul>

<h2>How to read them with OBD2Desk</h2>
<ol class="lista-pasos">
<li>Connect with a <a href="{guia:cable-kkl}">KKL cable</a>, ignition on or engine running.</li>
<li>In <em>Measured values</em>, check the engine type under <em>Engine</em> and tick the groups you want.</li>
<li>Click a row to see it in the <strong>live graph</strong>; with Ctrl+click you can compare up to four, for example specified and actual boost.</li>
<li>Click <strong>Record CSV</strong> to save a test and analyse it later in the viewer. Road tests always with a passenger handling the laptop, and only where it is safe.</li>
</ol>
<p>If something does not add up, the program's AI assistant can read these groups itself and tell you what to check.</p>
""",
    ),
]
