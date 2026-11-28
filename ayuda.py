"""
Textos del manual de la pestaña «Ayuda».

secciones() devuelve [(título, [párrafo, ...]), ...] ya traducidos. Un párrafo que
empieza por «• » se muestra como punto de una lista. Las traducciones están en
textos_en.py, como el resto de la interfaz.
"""
from idioma import tr


def secciones():
    return [
        (tr("Primeros pasos"), [
            tr("OBD2Desk lee averías y valores en vivo del coche con un cable conectado al conector de "
               "diagnóstico (bajo el volante) y te ayuda a interpretarlos con un asistente de IA."),
            tr("• Sin coche: elige el puerto «Simulador (sin coche)», pulsa Conectar y prueba todas las pestañas."),
            tr("• En el coche: conecta el cable al conector OBD y al ordenador, pon el contacto (para leer "
               "averías no hace falta arrancar), elige Conexión y Puerto y pulsa Conectar."),
            tr("• La conexión tarda unos segundos: con KKL de 2 a 6 s y con ELM327 hasta 25 s mientras busca el protocolo."),
            tr("• Lo habitual: leer las averías (pestaña Averías), mirar los valores en vivo (Panel o Valores "
               "medidos) y, si quieres, pedir ayuda al Asistente IA."),
        ]),
        (tr("Conexión y cables"), [
            tr("En la parte de arriba eliges el tipo de conexión, el puerto y, con KKL, el módulo del coche."),
            tr("• KKL · VAG KW1281: para coches del grupo VAG (SEAT, VW, Audi, Skoda) hasta 2004 "
               "aproximadamente, que no tienen OBD2 genérico. Necesita un cable «KKL 409.1» con chip FTDI "
               "(no sirven los CH340 ni PL2303). El selector Módulo elige la centralita: 01 motor, 03 ABS, "
               "15 airbag, 17 cuadro, etc."),
            tr("• ELM327 · OBD2 genérico: para cualquier coche con OBD2 (gasolina desde 2001 y diésel desde "
               "2004 en Europa, aproximadamente). Sirven los ELM327 USB, Bluetooth clásico y WiFi. Los que solo "
               "son Bluetooth LE (algunos para iPhone) no funcionan."),
            tr("• Puerto: el botón ↻ vuelve a buscar los puertos. Un ELM327 Bluetooth hay que emparejarlo antes "
               "en el sistema (en Windows aparece como puerto COM; en Linux, como /dev/rfcomm0). Para WiFi, "
               "conecta el ordenador a la red del adaptador y elige «WiFi · 192.168.0.10:35000» o escribe otra "
               "dirección ip:puerto."),
            tr("• Si no conecta: comprueba el contacto, el puerto y el cable. En Windows conviene poner la "
               "latencia del cable FTDI a 1 ms; en Linux tu usuario debe estar en el grupo dialout (el programa "
               "te dice el comando). Una radio no original puede bloquear la línea K en coches antiguos."),
        ]),
        (tr("Panel"), [
            tr("Relojes y gráficas de los valores principales del motor. Pulsa «Iniciar lectura» para empezar y "
               "«Detener» para parar."),
            tr("• Con KKL (diésel TDI): régimen, caudal inyectado, presión del turbo (con la marca de la presión "
               "teórica), temperatura, ciclo de la N75 y de la EGR, y gráficas del turbo y de la masa de aire "
               "teóricos frente a reales."),
            tr("• Con KKL en un gasolina (selector Motor de Valores medidos): régimen, carga, temperaturas, "
               "tiempo de inyección, masa de aire, mariposa, avance de encendido y tensión."),
            tr("• Con ELM327: régimen, velocidad, temperatura, carga, temperatura de admisión, masa de aire, "
               "mariposa y tensión, con gráficas del régimen y de la carga."),
        ]),
        (tr("Valores medidos"), [
            tr("Lectura de los valores que tú elijas, en una tabla en vivo."),
            tr("• Con KKL marcas los grupos de valores medidos o escribes otros números de grupo. Arriba, en "
               "Motor, eliges el tipo de motor (TDI de bomba rotativa, TDI inyector-bomba o gasolina) para ver "
               "sus grupos habituales con el nombre de cada valor; al conectar a la centralita del motor se "
               "elige solo. Con ELM327 eliges en la lista los valores (PIDs) que da tu coche; Ctrl+clic o "
               "Mayús+clic para elegir varios."),
            tr("• Haz clic en una fila de la tabla para ver su gráfica (Ctrl+clic, hasta 4 a la vez). El "
               "programa guarda el último minuto de todos los valores, así que la gráfica sale con su historia."),
            tr("• «Grabar CSV» guarda los valores en un archivo que se abre en Excel o LibreOffice; «Abrir CSV...» "
               "abre una grabación en el visor, donde puedes elegir columnas, hacer zoom arrastrando con el ratón "
               "y ver el mínimo, la media y el máximo."),
        ]),
        (tr("Averías"), [
            tr("• «Leer averías» muestra los códigos con su descripción. Con ELM327 salen las memorizadas, las "
               "pendientes y las permanentes (estas no se pueden borrar: desaparecen solas cuando el coche "
               "comprueba que el fallo se ha arreglado), y a la derecha los datos congelados del momento en que "
               "se encendió el testigo."),
            tr("• «Borrar averías» las borra de la centralita (con el contacto puesto y el motor parado). Anótalas "
               "antes: si el fallo sigue, volverán."),
            tr("• «Escanear todos los módulos» (KKL) recorre todas las centralitas del coche y lista las averías "
               "de cada una. Tarda unos minutos y se puede detener."),
            tr("• «Test de actuadores...» (KKL) hace que la centralita active uno a uno sus componentes (relés, "
               "electroválvulas, inyectores, testigos) para comprobar que funcionan: se oye un clic o un zumbido, o se "
               "enciende un testigo. Con el motor parado y el contacto puesto. Cada componente sigue activo hasta que "
               "pasas al siguiente o pulsas «Terminar»."),
            tr("• «Generar informe» crea una página con los datos del coche y las averías que se abre en el "
               "navegador y se puede imprimir o guardar como PDF."),
            tr("• Historial: cada lectura se guarda sola por coche. Debajo de los botones verás qué averías son "
               "nuevas, cuáles ya no aparecen y cuáles se repiten respecto al diagnóstico anterior; «Historial...» "
               "abre todos los diagnósticos guardados."),
        ]),
        (tr("Vehículo"), [
            tr("Datos de identificación del coche y de la centralita, que se leen al conectar."),
            tr("• Con KKL: referencia de la centralita, componente, versión de software y codificación."),
            tr("• Con ELM327: protocolo, VIN decodificado (marca, país y año), tensión de batería, calibración "
               "de la centralita y, a la derecha, los monitores de preparación. Antes de la ITV conviene que "
               "estén todos completos: después de borrar averías tardan unos días de uso en completarse."),
        ]),
        (tr("Consumo y 0-100"), [
            tr("Consumo instantáneo y medio del trayecto y, con ELM327, cronómetro de 0 a 100 km/h. Pulsa "
               "«Iniciar lectura»; «Reiniciar trayecto» pone a cero el consumo medio, los litros y la distancia."),
            tr("• El consumo es una estimación (±10 %) calculada con el aire que entra al motor o el combustible "
               "inyectado. Ajusta el Combustible y la Cilindrada (o los Cilindros con KKL) para que salga bien."),
            tr("• En diésel por OBD2 solo se calcula si el coche da la sonda lambda de banda ancha."),
            tr("• Cronómetro 0-100: con el coche parado se arma solo y empieza a contar al salir. Da también el "
               "tiempo hasta 50 km/h y guarda las últimas medidas. Se anula si frenas o paras antes de llegar. "
               "Hazlo solo en un sitio seguro y sin tráfico."),
            tr("• Con KKL, un TDI no da la velocidad: solo hay consumo en litros por hora. En un gasolina con los "
               "grupos estándar (002 y 005) hay consumo en L/100 km, distancia y cronómetro 0-100."),
        ]),
        (tr("Asistente IA"), [
            tr("El asistente analiza las averías y los valores del coche y te guía en el diagnóstico: puede leer "
               "averías y valores, grabar unos segundos de datos, consultar el historial o pedirte que hagas "
               "algo (arrancar, acelerar, etc.)."),
            tr("• Necesita una API key de un proveedor (Anthropic, OpenAI o DeepSeek): elige el proveedor, pulsa "
               "«Conseguir una API key», pégala y pulsa Guardar. Cada consulta la cobra el proveedor a tu cuenta."),
            tr("• Conecta con el coche, pulsa «Analizar averías del vehículo» o escribe tu problema (por ejemplo, "
               "«tira poco por encima de 3000 rpm») y sigue sus indicaciones."),
            tr("• Al analizar se envían al proveedor los datos del vehículo (incluido el VIN), las averías y los "
               "valores. La IA puede equivocarse: confirma el diagnóstico antes de cambiar piezas."),
        ]),
        (tr("Registro"), [
            tr("Muestra lo que va haciendo el programa y los errores de comunicación. Si algo falla, marca "
               "«Mostrar comunicación detallada» para ver cada mensaje con el coche; en el Asistente IA, «Analizar "
               "errores del programa» envía este registro a la IA para que te ayude."),
        ]),
        (tr("Archivos y configuración"), [
            tr("• Las grabaciones CSV y los informes se guardan junto al programa (en Linux, en Documentos/OBD2Desk)."),
            tr("• La configuración, la API key y el historial de cada coche se guardan en la carpeta de "
               "configuración de tu usuario (Windows: %APPDATA%\\OBD2Desk; Linux: ~/.config/OBD2Desk)."),
            tr("• El idioma se cambia con el selector junto al nombre del programa. Cuando hay una versión nueva "
               "aparece un aviso arriba; haz clic para descargarla."),
        ]),
    ]
