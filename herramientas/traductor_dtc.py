"""
Traductor al español de los títulos de los códigos de avería genéricos (SAE J2012) de OBDex.

Los títulos en inglés son fórmulas: [componente] [fallo] [posición], p. ej.
«Exhaust Gas Temperature Sensor Circuit Low Bank 1 Sensor 2». El traductor:
  1. aplica las plantillas fijas («Lost Communication With X», «Invalid Data Received From X»…);
  2. separa la posición (banco, sensor) y el fallo (por la derecha, con FALLOS);
  3. traduce el componente por unidades (diccionario NOMBRES/ADJETIVOS, frases de varias palabras
     primero) y las recompone en el orden del español, con artículo y concordancia de género:
     Exhaust Gas · Temperature · Sensor  →  «Sensor de temperatura de los gases de escape».
Si algo no está en el diccionario devuelve None (el programa enseña entonces el título en inglés).

Lo usa herramientas/codigos_genericos.py para generar obd_codigos.py.
"""
import re

# ---------------------------------------------------------------------------
# Nombres: inglés -> (español, género, artículo)
#   género: m, f, mp, fp     artículo: 1 = «del/de la…» como complemento, 0 = «de»
# Las frases de varias palabras tienen prioridad (se busca la más larga).
# ---------------------------------------------------------------------------
_N = """
Circuit|circuito|m|1
Sensor|sensor|m|1
Sensors|sensores|mp|1
Control|control|m|1
Controls|mandos|mp|1
Module|módulo|m|1
Control Module|módulo de control|m|1
Temperature|temperatura|f|0
Battery|batería|f|1
Position|posición|f|0
Pressure|presión|f|0
Range|rango|m|1
Cylinder|cilindro|m|1
Fuel|combustible|m|0
Voltage|tensión|f|0
Valve|válvula|f|1
Valves|válvulas|fp|1
Communication|comunicación|f|0
System|sistema|m|1
Motor|motor|m|1
Coolant|refrigerante|m|1
Engine Coolant|refrigerante del motor|m|1
Actuator|actuador|m|1
Switch|interruptor|m|1
Pump|bomba|f|1
Air|aire|m|1
Current|corriente|f|0
Data|datos|mp|0
Solenoid|electroválvula|f|1
Exhaust|escape|m|0
Exhaust Gas|gases de escape|mp|1
Drive|tracción|f|0
Drive Motor|motor de tracción|m|1
Engine|motor|m|1
Injector|inyector|m|1
Fuel Injector|inyector|m|1
Sense|detección|f|0
Transmission|cambio|m|1
Transmission Fluid|aceite del cambio|m|1
Transmission Range|selector del cambio|m|1
Intake|admisión|f|0
Intake Air|aire de admisión|m|1
Intake Manifold|colector de admisión|m|1
Exhaust Manifold|colector de escape|m|1
Shift|cambio de marcha|m|1
Shift Solenoid|electroválvula de cambio|f|1
Shift Fork|horquilla de cambio|f|1
Brake|freno|m|1
Brakes|frenos|mp|1
Brake Pedal|pedal del freno|m|1
Brake Booster|servofreno|m|1
Brake Switch|interruptor del freno|m|1
Heater|calefactor|m|1
Reductant|agente reductor|m|1
Camshaft|árbol de levas|m|1
Speed|velocidad|f|0
Turbocharger|turbocompresor|m|1
Supply|alimentación|f|0
Pack|paquete|m|1
O2 Sensor|sonda lambda|f|1
O2|oxígeno|m|0
HO2S|sonda lambda|f|1
Clutch|embrague|m|1
Charger|cargador|m|1
Phase|fase|f|1
Signal|señal|f|0
Signals|señales|fp|0
DC/DC Converter|convertidor CC/CC|m|1
DC|CC|f|0
Injection|inyección|f|0
Power|potencia|f|0
Power Steering|dirección asistida|f|1
Power Window|elevalunas eléctrico|m|1
Flow|caudal|m|0
Fluid|líquido|m|1
Bypass|bypass|m|1
Input|entrada|f|0
Supercharger|compresor volumétrico|m|1
Gear|marcha|f|1
Gears|marchas|fp|1
Generator|generador|m|1
EGR|EGR|f|1
EGR Valve|válvula EGR|f|1
EGR Cooler|enfriador de la EGR|m|1
Throttle|mariposa|f|1
Throttle/Pedal|mariposa/pedal|f|1
Throttle Body|cuerpo de mariposa|m|1
Limit|límite|m|1
Limits|límites|mp|1
Seat|asiento|m|1
Bus|bus|m|1
Ignition|encendido|m|1
Ignition Switch|conmutador de encendido|m|1
Start|arranque|m|1
Converter|convertidor|m|1
Torque Converter|convertidor de par|m|1
Door|puerta|f|1
Wheel|rueda|f|1
Charge|carga|f|0
Charge Air|aire de sobrealimentación|m|1
Charge Air Cooler|intercooler|m|1
Vehicle|vehículo|m|1
Charging|carga|f|0
Charging System|sistema de carga|m|1
Pedal|pedal|m|1
Accelerator Pedal|pedal del acelerador|m|1
Cooler|enfriador|m|1
Tank|depósito|m|1
Fuel Tank|depósito de combustible|m|1
Inverter|inversor|m|1
Glow Plug|bujía de precalentamiento|f|1
Glow Plugs|bujías de precalentamiento|fp|1
EVAP|EVAP|m|0
EVAP System|sistema EVAP|m|1
Cold Start|arranque en frío|m|1
Timing|sincronización|f|0
Injection Timing|avance de la inyección|m|1
Deployment|disparo|m|1
Deployment Loop|circuito de disparo|m|1
Deployment Control|control de disparo|m|1
Level|nivel|m|1
Contactor|contactor|m|1
Particulate Matter|partículas|fp|0
Particulate Filter|filtro de partículas|m|1
Diesel Particulate Filter|filtro de partículas diésel|m|1
Output|salida|f|0
Electronics|electrónica|f|1
Gas|gas|m|1
Catalyst|catalizador|m|1
Steering|dirección|f|1
Steering Wheel|volante|m|1
Steering Column|columna de dirección|f|1
Steering Angle|ángulo de giro|m|1
Compressor|compresor|m|1
AC Compressor|compresor del A/A|m|1
A/C Compressor|compresor del A/A|m|1
Fan|ventilador|m|1
Cooling Fan|ventilador de refrigeración|m|1
Learning|aprendizaje|m|0
Boost|sobrealimentación|f|0
Boost Pressure|presión de sobrealimentación|f|0
Deactivation|desactivación|f|0
Relay|relé|m|1
Relays|relés|mp|1
Booster|amplificador|m|1
Profile|perfil|m|1
Manifold|colector|m|1
Park|posición P|f|0
Park Brake|freno de estacionamiento|m|1
Parking Brake|freno de estacionamiento|m|1
Interlock|bloqueo|m|1
4WD|tracción 4x4|f|1
Four-Wheel Drive|tracción 4x4|f|1
AWD|tracción total|f|1
Filter|filtro|m|1
Cell|celda|f|1
Regulator|regulador|m|1
Outlet|salida|f|1
Reference|referencia|f|0
Reference Voltage|tensión de referencia|f|0
Belt|correa|f|1
Seat Belt|cinturón de seguridad|m|1
Seatbelt|cinturón de seguridad|m|1
Lock|bloqueo|m|1
Leak|fuga|f|1
Interface|interfaz|f|1
Inlet|entrada|f|1
Cooling|refrigeración|f|0
Cooling System|sistema de refrigeración|m|1
Oil|aceite|m|1
Engine Oil|aceite del motor|m|1
Unit|unidad|f|1
Ratio|relación|f|0
Select|selección|f|0
Mode|modo|m|1
Offset|desviación|f|0
Restraints|sistema de retención|m|1
Restraint|retención|f|0
Restraint System|sistema de retención|m|1
Torque|par|m|1
Balancing|equilibrado|m|0
Cell Balancing|equilibrado de celdas|m|0
Starter|motor de arranque|m|1
Starter Motor|motor de arranque|m|1
Row|fila|f|1
Ion|iones|mp|0
Ion Current|corriente de iones|f|0
Shaft|eje|m|1
Output Shaft|eje de salida|m|1
Input Shaft|eje de entrada|m|1
Fork|horquilla|f|1
Detection|detección|f|0
Coil|bobina|f|1
Ignition Coil|bobina de encendido|f|1
ABS|ABS|m|1
Trim|corrección|f|0
Fuel Trim|corrección de combustible|f|0
Grille|parrilla|f|1
Shutter|persiana|f|1
Grille Air Shutter|persiana de la parrilla|f|1
Diesel|diésel|m|0
Coupler|acoplador|m|1
Combustion|combustión|f|0
Aftertreatment|postratamiento|m|1
Exhaust Aftertreatment|postratamiento de gases de escape|m|1
Request|petición|f|0
Side|lado|m|1
Passenger|acompañante|m|1
Driver|conductor|m|1
Response|respuesta|f|0
Rocker Arm|balancín|m|1
AIR|aire secundario|m|1
Secondary Air|aire secundario|m|1
Purge|purga|f|0
Cruise Control|control de crucero|m|1
Rail|rail|m|1
Fuel Rail|rail de combustible|m|1
Time|tiempo|m|0
Element|elemento|m|1
Lever|palanca|f|1
Disconnect|desconexión|f|0
Refrigerant|refrigerante del A/A|m|1
Air-Fuel|aire-combustible|m|0
Air-Fuel Ratio|relación aire-combustible|f|0
Imbalance|desequilibrio|m|0
Threshold|umbral|m|1
Vacuum|vacío|m|0
Friction|fricción|f|0
Indicator|indicador|m|1
Metering|dosificación|f|0
Vibration|vibración|f|0
Idle|ralentí|m|1
Idle Air Control|control del aire de ralentí|m|1
Knock|picado|m|0
Knock/Combustion Vibration Sensor|sensor de picado/vibración de combustión|m|1
Runner|conducto|m|1
Runners|conductos|mp|1
Turbine|turbina|f|1
Pulse|impulso|m|0
Loop|lazo|m|1
Closed Loop|lazo cerrado|m|0
Error|error|m|0
PCM|PCM|m|1
ECM|ECM|m|1
ECM/PCM|ECM/PCM|m|1
TCM|TCM|m|1
Pilot|piloto|m|1
Lamp|testigo|m|1
Volume|volumen|m|0
Shutoff|corte|m|0
Fuel Shutoff|corte de combustible|m|0
Processing|procesamiento|m|0
Pretensioner|pretensor|m|1
Acceleration|aceleración|f|0
Calibration|calibración|f|0
Port|puerto|m|1
Image|imagen|f|1
Washer|lavaparabrisas|m|1
PTO|toma de fuerza|f|1
Pumping|bombeo|m|0
AC|aire acondicionado|m|1
A/C|aire acondicionado|m|1
Air Conditioning|aire acondicionado|m|1
Stop|parada|f|0
Stop-Start|arranque y parada automática|m|1
Wastegate|wastegate|f|1
Volt|voltios|mp|0
Regeneration|regeneración|f|0
Misfire|fallo de encendido|m|0
Variation|variación|f|0
Switching|conmutación|f|0
Enable|habilitación|f|0
Group|grupo|m|1
CAN|CAN|m|0
Stage|etapa|f|1
HVAC|climatización|f|1
Cam|leva|f|1
Rotor|rotor|m|1
Fill|llenado|m|0
Neutral|punto muerto|m|1
Balance|equilibrio|m|0
Crankcase|cárter|m|1
Crankcase Ventilation|ventilación del cárter|f|1
Occupant|ocupante|m|1
Feedback|realimentación|f|0
Tuning|ajuste|m|0
Load|carga|f|0
Disable|desactivación|f|0
Crankshaft|cigüeñal|m|1
Efficiency|eficiencia|f|0
Management|gestión|f|0
Gate|compuerta|f|1
Precharge|precarga|f|0
Camera|cámara|f|1
Window|ventanilla|f|1
Status|estado|m|0
Effort|esfuerzo|m|0
Transfer|transferencia|f|0
Transfer Case|caja de transferencia|f|1
Mass|masa|f|0
Mass Air Flow|caudal de aire|m|0
Mass or Volume Air Flow|caudal de aire|m|0
MIL|testigo de avería (MIL)|m|1
Body|carrocería|f|1
Body Control Module|módulo de control de la carrocería|m|1
Processor|procesador|m|1
Shutdown|apagado|m|0
Heat|calor|m|0
Heat Exchanger|intercambiador de calor|m|1
Accessory|accesorios|mp|1
Lighting|iluminación|f|1
Vaporizer|vaporizador|m|1
Hydrogen|hidrógeno|m|0
Case|caja|f|1
Vent|ventilación|f|0
Pawl|trinquete|m|1
Quality|calidad|f|0
Display|pantalla|f|1
Piston|pistón|m|1
Ventilation|ventilación|f|0
NH3|NH3|m|0
NOx|NOx|m|0
Classification|clasificación|f|0
Monitoring|supervisión|f|0
Headlamp|faro|m|1
Headlamps|faros|mp|1
Monitor|monitor|m|1
Angle|ángulo|m|1
Selector|selector|m|1
Reservoir|depósito|m|1
Memory|memoria|f|1
Audio|audio|m|0
Adjustment|ajuste|m|0
Suspension|suspensión|f|1
Illumination|iluminación|f|0
Distribution|distribución|f|0
IMT|IMT|m|1
Resistance|resistencia|f|0
Stroke|carrera|f|0
Radiator|radiador|m|1
Head|culata|f|1
Cylinder Head|culata|f|1
Condition|condición|f|0
Conditions|condiciones|fp|0
PCV|PCV|m|0
PCV Valve|válvula PCV|f|1
Wake-up|activación|f|0
Wake-Up|activación|f|0
Reverse|marcha atrás|f|1
Energy|energía|f|0
Water|agua|f|0
Ozone|ozono|m|0
Reduction|reducción|f|0
Ground|masa|f|0
Traction|tracción|f|0
Traction Control|control de tracción|m|1
Tire|neumático|m|1
Tire Pressure|presión de los neumáticos|f|0
Vapor|vapor|m|0
Contribution|contribución|f|0
Compression|compresión|f|0
Radar|radar|m|1
Assist|asistencia|f|0
Direction|sentido|m|0
Rate|velocidad|f|0
Roll Rate|velocidad de balanceo|f|0
Yaw Rate|velocidad de guiñada|f|0
Thermostat|termostato|m|1
Restriction|restricción|f|0
Distance|distancia|f|0
Cap|tapón|m|1
Fuel Cap|tapón del depósito|m|1
Inhibit|inhibición|f|0
Blower|ventilador|m|1
Component|componente|m|1
Resolution|resolución|f|0
Proximity|proximidad|f|0
Sound|sonido|m|0
Selection|selección|f|0
Gateway|pasarela|f|1
Anode|ánodo|m|1
Airbag|airbag|m|1
Limiter|limitador|m|1
Alert|alerta|f|1
Discharge|descarga|f|0
Excitation|excitación|f|0
Lift|alzada|f|0
Valve Lift|alzada de válvula|f|0
TCS|control de tracción|m|1
Frequency|frecuencia|f|0
Air Dam|deflector de aire|m|1
Service|servicio|m|0
Trailer|remolque|m|1
TPMS|TPMS|m|1
Measurement|medición|f|0
Activity|actividad|f|0
RPM|régimen|m|0
Engine RPM|régimen del motor|m|0
Engine Speed|régimen del motor|m|0
Slip|deslizamiento|m|0
Thickness|grosor|m|0
Disc|disco|m|1
Player|reproductor|m|1
Changer|cambiador|m|1
Entertainment|entretenimiento|m|0
Obstacle|obstáculos|mp|0
Pedestrian|peatón|m|1
Pedestrian Protection|protección de peatones|f|1
Mirror|retrovisor|m|1
Mirrors|retrovisores|mp|1
Parking|aparcamiento|m|0
Parking Assist|ayuda al aparcamiento|f|1
Relief|alivio|m|0
Hose|manguito|m|1
Fuse|fusible|m|1
Adsorber|adsorbedor|m|1
Deceleration|deceleración|f|0
Sample|muestra|f|0
Stabilization|estabilización|f|0
Stabilisation|estabilización|f|0
Column|columna|f|1
Curtain|cortina|f|1
Roll|balanceo|m|0
Cleaning|limpieza|f|0
Recirculation|recirculación|f|0
Wiper|limpiaparabrisas|m|1
Evaporator|evaporador|m|1
Driveline|transmisión|f|1
Safety|seguridad|f|0
Humidity|humedad|f|0
Immobilizer|inmovilizador|m|1
Mount|soporte|m|1
Leakage|fuga|f|0
Accumulation|acumulación|f|0
Chassis|chasis|m|1
AFCM|AFCM|m|1
Information|información|f|0
Convenience|confort|m|0
Drain|drenaje|m|0
Knee|rodilla|f|0
Release|liberación|f|0
Amplifier|amplificador|m|1
Tone Wheel|rueda fónica|f|1
Warning|aviso|m|0
Height|altura|f|0
Ride Height|altura de la carrocería|f|0
Blending|mezcla|f|0
MAP|MAP|m|0
MAF|MAF|m|0
Composition|composición|f|0
Refueling|repostaje|m|0
Connection|conexión|f|0
Economy|economía|f|0
Consumption|consumo|m|0
Fuel Consumption|consumo de combustible|m|0
Sensing|detección|f|0
Hood|capó|m|1
Kick Down|kick-down|m|1
Movement|movimiento|m|0
Motion|movimiento|m|0
Return|retorno|m|0
Interstage|entre etapas|m|0
Radio|radio|f|1
Cathode|cátodo|m|1
Tension|tensión|f|0
LIDAR|LIDAR|m|1
Night Vision|visión nocturna|f|0
Sunroof|techo solar|m|1
High Beam|luz de carretera|f|1
Low Beam|luz de cruce|f|1
Beam|haz|m|1
Turn Signal|intermitente|m|1
Channel|canal|m|1
Axle|eje|m|1
Dynamics|dinámica|f|0
VIN|VIN|m|1
Damping|amortiguación|f|0
State|estado|m|0
Timer|temporizador|m|1
Distributor|distribuidor|m|1
Servo|servo|m|1
Accelerator|acelerador|m|1
Terminal|borne|m|1
Accumulator|acumulador|m|1
Step|paso|m|1
Soot|hollín|m|0
Additive|aditivo|m|1
Reagent|reactivo|m|1
Sequence|secuencia|f|0
Navigation|navegación|f|0
Security|seguridad|f|0
Leveling|nivelación|f|0
Roof|techo|m|1
Object|objeto|m|1
Objects|objetos|mp|1
Maintenance|mantenimiento|m|0
Entrapment|atrapamiento|m|0
Running Board|estribo|m|1
Feature|función|f|1
Comfort|confort|m|0
Stack|pila|f|1
Fuel Cell|pila de combustible|f|1
Fuel Cell Stack|pila de combustible|f|1
Recline|reclinación|f|0
Buckle|hebilla|f|1
Sun Load|radiación solar|f|0
Mix|mezcla|f|0
Rain|lluvia|f|0
Backup Camera|cámara de marcha atrás|f|1
Back|respaldo|m|1
Seat Back|respaldo del asiento|m|1
Antenna|antena|f|1
Travel|recorrido|m|0
Stability|estabilidad|f|0
Chamber|cámara|f|1
Device|dispositivo|m|1
Receiver|receptor|m|1
Cranking|arranque|m|0
Road|carretera|f|0
Fresh Air|aire exterior|m|1
Key|llave|f|1
Field|campo|m|0
Configuration|configuración|f|0
Event Data Recorder|registrador de datos de accidente|m|1
Event|evento|m|1
Recorder|registrador|m|1
Cleaner|limpiador|m|1
Air Cleaner|filtro de aire|m|1
Degassing|desgasificación|f|0
Tensioner|tensor|m|1
Instrument Panel|cuadro de instrumentos|m|1
Instrument Cluster|cuadro de instrumentos|m|1
Cluster|cuadro|m|1
Function|función|f|0
Actuation|accionamiento|m|0
Protocol|protocolo|m|1
Evaporative Emission|emisiones evaporativas|fp|0
Emission|emisión|f|0
Emissions|emisiones|fp|0
Authentication|autenticación|f|0
Header|colector|m|1
Mixing|mezcla|f|0
Bolster|refuerzo|m|1
Track|guía|f|1
Seat Track|guía del asiento|f|1
Speaker|altavoz|m|1
Bag|bolsa|f|1
License Plate|matrícula|f|1
Light|luz|f|1
Defrost|desempañado|m|0
Bluetooth|Bluetooth|m|1
PWM|PWM|m|0
BSCM|BSCM|m|1
BTSI|BTSI|m|1
Separation|separación|f|0
Propulsion|propulsión|f|0
Hardware|hardware|m|0
Software|software|m|0
Synchronization|sincronización|f|0
Orifice|orificio|m|1
KAM|memoria KAM|f|1
Access|acceso|m|0
RAM|RAM|f|1
ROM|ROM|f|1
VSS|VSS|m|1
PRNDL|PRNDL|m|1
Conversion|conversión|f|0
Discharging|descarga|f|0
Blockage|obstrucción|f|0
Substrate|sustrato|m|1
Inducement|limitación por agente reductor|f|0
HC|HC|m|0
Adsorption|adsorción|f|0
Ash|ceniza|f|0
Duration|duración|f|0
L-Terminal|borne L|m|1
Number|número|m|0
Feedgas|gases de entrada|mp|1
Pre-Ignition|preencendido|m|0
Terrain|terreno|m|0
Compass|brújula|f|1
Global Positioning|GPS|m|1
Television|televisión|f|0
Personal Computer|ordenador personal|m|1
Subscription|suscripción|f|0
Telephone|teléfono|m|1
Tachograph|tacógrafo|m|1
Folding Top|capota plegable|f|1
Top|capota|f|1
Impact|impacto|m|1
Transceiver|transceptor|m|1
Speech Recognition|reconocimiento de voz|m|0
Integration|integración|f|0
Localization|localización|f|0
Mapping|mapeado|m|0
Certificate|certificado|m|1
Expander|expansor|m|1
Backpressure|contrapresión|f|0
Duct|conducto|m|1
Defroster|desempañador|m|1
Defogger|desempañador|m|1
Command|orden|f|0
Auto-Leveling|autonivelación|f|0
Fog Lamp|faro antiniebla|m|1
Fog Lamps|faros antiniebla|mp|1
Marker Lamp|luz de gálibo|f|1
Trunk Lid|tapa del maletero|f|1
Tilt|inclinación|f|0
USB|USB|m|1
Hub|concentrador|m|1
Microphone|micrófono|m|1
Backlight|retroiluminación|f|0
Rotation|rotación|f|0
Lining|forro|m|1
Wear|desgaste|m|0
Pitch|cabeceo|m|0
Diameter|diámetro|m|0
Block|bloque|m|1
Cylinder Block|bloque motor|m|1
Modulation|modulación|f|0
EBCM|EBCM|m|1
Bias|desviación|f|0
Encoder|codificador|m|1
Coupling|acoplamiento|m|1
EBBC|EBBC|m|1
Connector|conector|m|1
Protection|protección|f|0
Force|fuerza|f|0
Initiator|iniciador|m|1
Oxygen|oxígeno|m|0
Controller|controlador|m|1
EEPROM|EEPROM|f|1
NVRAM|NVRAM|f|1
Odometer|cuentakilómetros|m|1
Stabilizer|estabilizador|m|1
Alignment|alineación|f|0
Dosing|dosificación|f|0
Sulfur|azufre|m|0
Insulation|aislamiento|m|0
IPC|IPC|m|1
Expansion|expansión|f|0
Windshield|parabrisas|m|1
Cutoff|corte|m|0
Identification|identificación|f|0
Clock|reloj|m|1
Hybrid/EV Battery|batería de alta tensión|f|1
Hybrid/EV Battery Pack|paquete de la batería de alta tensión|m|1
Hybrid/EV System|sistema híbrido/eléctrico|m|1
Powertrain|grupo motopropulsor|m|1
Hybrid/EV Powertrain|grupo motopropulsor híbrido/eléctrico|m|1
Alternative Fuel|combustible alternativo|m|1
Fuel Pump|bomba de combustible|f|1
Fuel Volume Regulator|regulador de volumen de combustible|m|1
Fuel Pressure Regulator|regulador de presión de combustible|m|1
Fuel Level|nivel de combustible|m|1
Fuel System|sistema de combustible|m|1
Fuel Metering|dosificación de combustible|f|0
Injection Pump|bomba de inyección|f|1
Coolant Pump|bomba de refrigerante|f|1
Oil Pump|bomba de aceite|f|1
Water Pump|bomba de agua|f|1
Vacuum Pump|bomba de vacío|f|1
Exhaust Gas Recirculation|recirculación de gases de escape (EGR)|f|0
Catalyst System|sistema del catalizador|m|1
Wheel Speed|velocidad de rueda|f|0
Vehicle Speed|velocidad del vehículo|f|0
Turbine Speed|velocidad de la turbina|f|0
Brake Pressure|presión de frenado|f|0
Brake Fluid|líquido de frenos|m|1
Power Supply|alimentación|f|0
Ignition Input|entrada de encendido|f|0
Communication Bus|bus de comunicación|m|1
Vehicle Communication Bus|bus de comunicación del vehículo|m|1
High Speed CAN|CAN de alta velocidad|m|0
Medium Speed CAN|CAN de velocidad media|m|0
Low Speed CAN|CAN de baja velocidad|m|0
High Voltage System|sistema de alta tensión|m|1
High Voltage|alta tensión|f|0
Low Voltage|baja tensión|f|0
Battery Energy|energía de la batería|f|0
Battery Charging System|sistema de carga de la batería|m|1
Battery Charger|cargador de la batería|m|1
Hydraulic Release|liberación hidráulica|f|0
Seat Belt Pretensioner|pretensor del cinturón de seguridad|m|1
Occupant Classification|clasificación del ocupante|f|0
Side Obstacle Detection|detección de obstáculos laterales|f|0
Glow Plug Control Module|módulo de control de las bujías de precalentamiento|m|1
Ion Current Sense|detección por corriente de iones|f|0
Moveable Roof|techo móvil|m|1
Supply Line|línea de alimentación|f|1
Pressure Control Solenoid|electroválvula de control de presión|f|1
Engine Coolant Bypass Valve|válvula de bypass del refrigerante del motor|f|1
Active Grille Air Shutter|persiana activa de la parrilla|f|1
Camshaft Position|posición del árbol de levas|f|0
Crankshaft Position|posición del cigüeñal|f|0
Camshaft Position Actuator|actuador de posición del árbol de levas|m|1
Camshaft Profile|perfil del árbol de levas|m|1
Throttle Actuator|actuador de la mariposa|m|1
Throttle Position|posición de la mariposa|f|0
Pedal Position|posición del pedal|f|0
Engine Hot|motor caliente|m|0
Engine Disconnect Clutch|embrague de desconexión del motor|m|1
Disconnect Clutch|embrague de desconexión|m|1
Motor Electronics|electrónica del motor eléctrico|f|1
Proximity Detection|detección de proximidad|f|0
Cylinder Deactivation|desactivación de cilindros|f|0
Deactivation/Intake Valve|válvula de admisión/desactivación|f|1
Deactivation/Exhaust Valve|válvula de escape/desactivación|f|1
Intake Valve|válvula de admisión|f|1
Exhaust Valve|válvula de escape|f|1
Intake Valve Control|control de la válvula de admisión|m|1
Exhaust Valve Control|control de la válvula de escape|m|1
Injection Pulse|impulso de inyección|m|0
Particulate Matter Sensor|sensor de partículas|m|1
NOx Sensor|sensor de NOx|m|1
Hydrogen Tank|depósito de hidrógeno|m|1
Cathode Bypass Valve|válvula de bypass del cátodo|f|1
Anode Drain Valve|válvula de drenaje del ánodo|f|1
Anode Header|colector del ánodo|m|1
Coolant Mixing Valve|válvula mezcladora de refrigerante|f|1
Expander Inlet|entrada del expansor|f|1
Ignition Output|salida de encendido|f|0
Multi-axis Acceleration Sensor Module|módulo de sensores de aceleración multieje|m|1
Wheel Speed Sensor|sensor de velocidad de rueda|m|1
Tone|fónica|f|0
Interior Light|luz interior|f|1
Interior Lights|luces interiores|fp|1
Turn Signals|intermitentes|mp|1
Air Bag|airbag|m|1
Sensor/Switch|sensor/interruptor|m|1
Turbocharger/Supercharger|turbocompresor/compresor|m|1
4WD/AWD|tracción 4x4/total|f|1
Starter/Generator|motor de arranque/generador|m|1
DC/AC|CC/CA|f|0
Input/Turbine|entrada/turbina|f|0
Knock/Combustion Vibration|picado/vibración de combustión|m|0
Solenoid/Actuator|electroválvula/actuador|f|1
Flow/Pressure|caudal/presión|m|0
Park/Neutral|posición P/N|f|0
SCR|SCR|m|0
SCR NOx Catalyst|catalizador SCR de NOx|m|1
NOx Catalyst|catalizador de NOx|m|1
Quantity|cantidad|f|0
Cruise|crucero|m|0
Line|línea|f|1
Particulate|partículas|fp|0
Isolation|aislamiento|m|0
Throttle/Fuel|mariposa/combustible|m|0
Cam/Rotor/Injector|leva/rotor/inyector|m|0
Engagement|acoplamiento|m|0
Disengagement|desacoplamiento|m|0
Driving|conducción|f|0
Automated Driving System|sistema de conducción automatizada|m|1
Apply|aplicación|f|0
Pulses|impulsos|mp|0
Contribution/Balance|contribución/equilibrio|m|0
Inductive|inductiva|f|0
Four Wheel Drive|tracción 4x4|f|1
Unlock|desbloqueo|m|0
Friction Element|elemento de fricción|m|1
Engine Exhaust|escape del motor|m|1
Gear Lever|palanca de cambios|f|1
Run Position|posición de marcha|f|0
Start Position|posición de arranque|f|0
Accessory Position|posición de accesorios|f|0
Lock/Pawl|bloqueo/trinquete|m|1
Player/Changer|reproductor/cambiador|m|1
Rail/System|rail/sistema|m|1
Glow Plug/Heater|bujía de precalentamiento/calentador|f|1
On/Start|contacto/arranque|m|0
Tire Pressure Monitoring|control de la presión de los neumáticos|m|1
Tire Pressure Monitoring Sensor|sensor de presión de los neumáticos|m|1
Random/Multiple Cylinder|varios cilindros|mp|1
Upshift|cambio a marcha superior|m|0
Downshift|cambio a marcha inferior|m|0
Plug|bujía|f|1
Glow|incandescencia|f|0
Gear Shift|cambio de marchas|m|1
Gear Shift Lock|bloqueo del cambio|m|1
Shift Lock|bloqueo del cambio|m|1
A/C Refrigerant|refrigerante del A/A|m|1
Forward/Back|adelante/atrás|m|0
Up/Down|arriba/abajo|m|0
Memory Set|memorización|f|0
Set|ajuste|m|0
Planetary Gear Set|tren epicicloidal|m|1
All Wheel Drive|tracción total|f|1
All Terrain|todoterreno|m|0
V2X|V2X|m|1
Emissions Critical Control Information|información de control crítica para emisiones|f|0
Information Center|centro de información|m|1
Isolation/Voltage Stabilization|aislamiento/estabilización de tensión|m|0
Up and Down Shift Switch|interruptor de subida y bajada de marchas|m|1
ABS/TCS|ABS/TCS|m|1
Internal Control Module|módulo de control|m|1
Random Access Memory (RAM)|memoria RAM|f|1
Non-Volatile Random Access Memory (NVRAM)|memoria NVRAM|f|1
Read Only Memory (ROM)|memoria ROM|f|1
Keep Alive Memory (KAM)|memoria KAM|f|1
Crankshaft/Camshaft|cigüeñal/árbol de levas|m|1
Power/Ground|alimentación/masa|f|0
Water in Fuel|agua en el combustible|f|0
Recirculate Position|posición de recirculación|f|0
Hydraulic Pressure Unit|unidad de presión hidráulica|f|1
Fuel Fill Door|tapa del depósito|f|1
Open Request|petición de apertura|f|0
Air Assisted Injector|inyector asistido por aire|m|1
Engine Off Timer|temporizador de motor apagado|m|1
Run/Start Position|posición de marcha/arranque|f|0
Anti-Lock Brake System (ABS)|sistema antibloqueo de frenos (ABS)|m|1
Anti-Lock Brake System|sistema antibloqueo de frenos|m|1
Instrument Panel Cluster (IPC)|cuadro de instrumentos (IPC)|m|1
Instrument Panel Cluster|cuadro de instrumentos|m|1
Idle Control System|sistema de control del ralentí|m|1
Manifold Absolute Pressure/Barometric Pressure|presión absoluta del colector/presión barométrica|f|0
Manifold Absolute Pressure|presión absoluta del colector|f|0
Upshift/Skip Shift Solenoid|electroválvula de cambio ascendente/salto de marcha|f|1
Ignition/Distributor Engine Speed Input|entrada de régimen del encendido/distribuidor|f|0
AC/DC Converter|convertidor CA/CC|m|1
Air/Fuel|aire/combustible|m|0
Supplemental Inflatable Restraint (SIR)|sistema de airbags (SIR)|m|1
Transmission Control System|sistema de control del cambio|m|1
"""

# Adjetivos: inglés -> (masculino, femenino, «pre» si va delante del nombre en español)
_A = """
Rear|trasero|trasera
Front|delantero|delantera
Left|izquierdo|izquierda
Right|derecho|derecha
Upper|superior|superior
Lower|inferior|inferior
Middle|central|central
Center|central|central
Interior|interior|interior
Outside|exterior|exterior
External|externo|externa
Internal|interno|interna
Auxiliary|auxiliar|auxiliar
Electric|eléctrico|eléctrica
Electrical|eléctrico|eléctrica
Electronic|electrónico|electrónica
Hydraulic|hidráulico|hidráulica
Mechanical|mecánico|mecánica
Primary|primario|primaria
Secondary|secundario|secundaria
Second|segundo|segunda|pre
Third|tercer|tercera|pre
First|primer|primera|pre
Active|activo|activa
Adaptive|adaptativo|adaptativa
Automatic|automático|automática
Automated|automatizado|automatizada
Variable|variable|variable
Digital|digital|digital
Wireless|inalámbrico|inalámbrica
Remote|remoto|remota
Positive|positivo|positiva
Negative|negativo|negativa
Intermediate|intermedio|intermedia
Heated|calefactado|calefactada
Cold|frío|fría
Hot|caliente|caliente
Main|principal|principal
Master|principal|principal
Single|único|única
Multiple|múltiple|múltiple
Special Purpose|de uso especial|de uso especial
Generic|genérico|genérica
Integrated|integrado|integrada
Moveable|móvil|móvil
Collapsible|plegable|plegable
Folding|plegable|plegable
Inflatable|hinchable|hinchable
Alternative|alternativo|alternativa
Barometric|barométrico|barométrica
Absolute|absoluto|absoluta
Differential|diferencial|diferencial
Lateral|lateral|lateral
Longitudinal|longitudinal|longitudinal
Vertical|vertical|vertical
Thermal|térmico|térmica
Dry|seco|seca
Serial|serie|serie
Direct|directo|directa
Manual|manual|manual
Ambient|ambiente|ambiente
Frontal|frontal|frontal
Hybrid/EV|híbrido/eléctrico|híbrida/eléctrica
Multi-Function|multifunción|multifunción
Multifunction|multifunción|multifunción
Multi-axis|multieje|multieje
Planetary|planetario|planetaria
Audible|acústico|acústica
Aerodynamic|aerodinámico|aerodinámica
Telematic|telemático|telemática
Haptic|háptico|háptica
Off-Board|externo|externa
Anti-Tamper|antimanipulación|antimanipulación
Anti-Lock|antibloqueo|antibloqueo
In-Vehicle|del vehículo|del vehículo
Auto|automático|automática
Pre-Catalyst|antes del catalizador|antes del catalizador
Post Catalyst|después del catalizador|después del catalizador
Small|pequeño|pequeña
Large|grande|grande
Unmetered|no medido|no medida
Non-Volatile|no volátil|no volátil
Evaporative|evaporativo|evaporativa
Electric/Auxiliary|eléctrico/auxiliar|eléctrica/auxiliar
Personal|personal|personal
Global|global|global
Pilot|piloto|piloto
Vacuum|de vacío|de vacío
Fresh|fresco|fresca
Diesel|diésel|diésel
Low Pressure|de baja presión|de baja presión
High Pressure|de alta presión|de alta presión
Secondary|secundario|secundaria
Inductive|inductivo|inductiva
"""

# Fallos (al final del título): secuencia de palabras en inglés -> texto en español
_F = """
Circuit|circuito
Circuits|circuitos
Control Circuit|circuito de control
Circuit/Open|circuito abierto
Control Circuit/Open|circuito de control abierto
Circuit Open|circuito abierto
Open|circuito abierto
Circuit Low|circuito, valor bajo
Circuit High|circuito, valor alto
Control Circuit Low|circuito de control, valor bajo
Control Circuit High|circuito de control, valor alto
Low|valor bajo
High|valor alto
Circuit Range/Performance|circuito, fuera de rango o funcionamiento incorrecto
Control Circuit Range/Performance|circuito de control, fuera de rango o funcionamiento incorrecto
Range/Performance|fuera de rango o funcionamiento incorrecto
Circuit Performance|circuito, funcionamiento incorrecto
Performance|funcionamiento incorrecto
Control Performance|control, funcionamiento incorrecto
Circuit Intermittent|circuito intermitente
Circuit Intermittent/Erratic|circuito, señal intermitente o errática
Intermittent/Erratic|señal intermitente o errática
Intermittent|intermitente
Erratic|señal errática
Circuit Erratic|circuito, señal errática
Circuit Malfunction|circuito averiado
Malfunction|avería
Circuit Short to Ground|circuito, cortocircuito a masa
Short to Ground|cortocircuito a masa
Short to Battery|cortocircuito a positivo
Circuit Short to Battery|circuito, cortocircuito a positivo
Short Circuit|cortocircuito
Shorted|en cortocircuito
Circuit Shorted|circuito en cortocircuito
Stuck On|bloqueo en activado
Stuck Off|bloqueo en desactivado
Stuck Open|bloqueo en abierto
Stuck Closed|bloqueo en cerrado
Stuck|bloqueo
Stuck/Stalled|bloqueo o calado
Stuck/Open|bloqueo en abierto
Circuit Stuck On|circuito, bloqueo en activado
Circuit Stuck Off|circuito, bloqueo en desactivado
Performance/Stuck Off|funcionamiento incorrecto o bloqueo en desactivado
Circuit Performance/Stuck Off|circuito, funcionamiento incorrecto o bloqueo en desactivado
Performance/Stuck On|funcionamiento incorrecto o bloqueo en activado
Too High|valor demasiado alto
Too Low|valor demasiado bajo
Too Long|tiempo demasiado largo
Too Short|tiempo demasiado corto
Too Fast|demasiado rápido
Too Slow|demasiado lento
Too Lean|mezcla demasiado pobre
Too Rich|mezcla demasiado rica
Not Learned|aprendizaje no realizado
No Signal|sin señal
Circuit No Signal|circuito, sin señal
Off|desactivado
On|activado
Closed|cerrado
Correlation|correlación incorrecta
Circuit Correlation|circuito, correlación incorrecta
Performance - Over Retarded|funcionamiento incorrecto, demasiado retrasado
Performance - Over Advanced|funcionamiento incorrecto, demasiado adelantado
Over-Retarded|demasiado retrasado
Over-Advanced|demasiado adelantado
Over Retarded|demasiado retrasado
Over Advanced|demasiado adelantado
Timing Over-Retarded|sincronización demasiado retrasada
Timing Over-Advanced|sincronización demasiado adelantada
Exceeded Learning Limit|límite de aprendizaje superado
Learning Limit Exceeded|límite de aprendizaje superado
Missing Calibration|falta la calibración
Internal Failure|fallo interno
Internal Fault|fallo interno
Failure|fallo
Fault|fallo
Overspeed|exceso de régimen
Underspeed|régimen insuficiente
Overspeed/Air in System|exceso de régimen o aire en el sistema
Overtemperature|exceso de temperatura
Over Temperature|exceso de temperatura
Overcurrent|exceso de corriente
Leak Detected|fuga detectada
Detected|detectado
Not Detected|no detectado
Slow Response|respuesta lenta
Circuit Slow Response|circuito, respuesta lenta
Response|respuesta incorrecta
Error|error
Incorrect|incorrecto
Invalid|no válido
Invalid Data|datos no válidos
Implausible|no plausible
Disabled|desactivado
Locked|bloqueado
Restricted|obstruido
Leaking|con fuga
Delayed|retardado
Insufficient|insuficiente
Excessive|excesivo
Deteriorated|deteriorado
Deterioration|deterioro
Lean|mezcla pobre
Rich|mezcla rica
Missing|ausente
Mismatch|discrepancia
Incomplete|incompleto
Unexpected|inesperado
Blocked|obstruido
Unstable|inestable
Engaged|acoplado
Disengaged|desacoplado
Not Engaged|no acoplado
Activated|activado
Inactive|inactivo
Exceeded|superado
Limit Exceeded|límite superado
Max Limit|límite máximo
Min Limit|límite mínimo
Above Threshold|por encima del umbral
Below Threshold|por debajo del umbral
Efficiency Below Threshold|eficiencia por debajo del umbral
Higher Than Expected|más alto de lo esperado
Lower Than Expected|más bajo de lo esperado
Unable To Achieve|no se alcanza
Swapped|intercambiado
Duplicate|duplicado
Improper|incorrecto
Programming Error|error de programación
Checksum Error|error de suma de verificación
Signal Low|señal baja
Signal High|señal alta
Signal Invalid|señal no válida
Supply Circuit|circuito de alimentación
Supply Circuit Low|circuito de alimentación, valor bajo
Supply Circuit High|circuito de alimentación, valor alto
Supply Circuit/Open|circuito de alimentación abierto
Supply Circuit Range/Performance|circuito de alimentación, fuera de rango o funcionamiento incorrecto
Feedback Circuit|circuito de realimentación
Feedback Signal Low|señal de realimentación baja
Feedback Signal High|señal de realimentación alta
Sense Circuit|circuito de detección
Sense Circuit Low|circuito de detección, valor bajo
Sense Circuit High|circuito de detección, valor alto
Driver Current/Temperature Too High|corriente o temperatura de la etapa de salida demasiado alta
Circuit Driver Current/Temperature Too High|circuito, corriente o temperatura de la etapa de salida demasiado alta
Voltage Low|tensión baja
Voltage High|tensión alta
System Voltage Low|tensión del sistema baja
System Voltage High|tensión del sistema alta
Current Low|corriente baja
Current High|corriente alta
Pressure Low|presión baja
Pressure High|presión alta
Temperature Low|temperatura baja
Temperature High|temperatura alta
Temperature Too High|temperatura demasiado alta
Temperature Too Low|temperatura demasiado baja
Pressure Too High|presión demasiado alta
Pressure Too Low|presión demasiado baja
Speed Too High|velocidad demasiado alta
Speed Too Low|velocidad demasiado baja
Run Time Exceeded|tiempo de funcionamiento superado
Time Exceeded|tiempo superado
Incorrect Ratio|relación incorrecta
Electrical|fallo eléctrico
Secondary Circuit|circuito secundario
At Max Limit|en el límite máximo
At Min Limit|en el límite mínimo
Learning At Max Limit|aprendizaje en el límite máximo
Learning At Min Limit|aprendizaje en el límite mínimo
Biased/Stuck|desviado o bloqueado
Activated|activado
High Current|corriente alta
Low Current|corriente baja
Driver High Current|etapa de salida, corriente alta
Insufficient Flow|caudal insuficiente
Excessive Flow|caudal excesivo
Requested|solicitado
Not Requested|no solicitado
Installed|instalado
Limited|limitado
Isolation Fault|fallo de aislamiento
Out of Range|fuera de rango
Up|arriba
Down|abajo
No Activity Detected|sin actividad
No Activity|sin actividad
Rich to Lean|de rica a pobre
Lean to Rich|de pobre a rica
High to Low|de alto a bajo
Low to High|de bajo a alto
Delayed Response|respuesta retardada
Exceeded Control Limits|límites de control superados
At Limit|en el límite
At High Limit|en el límite superior
At Low Limit|en el límite inferior
Flow Too Low|caudal demasiado bajo
Flow Too High|caudal demasiado alto
Rough Idle|ralentí irregular
Stuck In Locked Position|bloqueado en la posición de bloqueo
Not Programmed or Incompatible|sin programar o incompatible
Not Programmed|sin programar
Incompatible|incompatible
Performance/Too Slow|funcionamiento incorrecto o demasiado lento
Performance/Too Fast|funcionamiento incorrecto o demasiado rápido
Performance/Too High|funcionamiento incorrecto o valor demasiado alto
Performance/Too Low|funcionamiento incorrecto o valor demasiado bajo
Adjustment At Limit|ajuste en el límite
Timing Over-Advanced or System Performance|avance excesivo de la sincronización o funcionamiento incorrecto
Timing Over-Retarded|retraso excesivo de la sincronización
Forced Limited Power|potencia limitada forzada
Forced Engine Shutdown|parada forzada del motor
Forced Idle|ralentí forzado
Forced Traction Control Disable|desactivación forzada del control de tracción
Minimum/Maximum Stop Performance|topes mínimo y máximo, funcionamiento incorrecto
Maximum Stop Performance|tope máximo, funcionamiento incorrecto
Minimum Stop Performance|tope mínimo, funcionamiento incorrecto
Incorrect Neutral Position Indicated|indica una posición de punto muerto incorrecta
Not Present|no presente
Biased/Stuck Lean|señal desviada o bloqueada en mezcla pobre
Biased/Stuck Rich|señal desviada o bloqueada en mezcla rica
Too Rich at Idle|mezcla demasiado rica al ralentí
Too Lean at Idle|mezcla demasiado pobre al ralentí
Too Rich Off Idle|mezcla demasiado rica fuera del ralentí
Too Lean Off Idle|mezcla demasiado pobre fuera del ralentí
Signals Swapped|señales intercambiadas
Internal Performance|funcionamiento interno incorrecto
Unrequested Movement|movimiento no solicitado
Exceeded Learning Limits|límites de aprendizaje superados
Calibration Not Learned/Programmed|calibración sin aprender o programar
Not Learned/Programmed|sin aprender o programar
Primary Control Circuit|circuito de control primario
Primary Control Circuit Low|circuito de control primario, valor bajo
Primary Control Circuit High|circuito de control primario, valor alto
Primary Control Circuit/Open|circuito de control primario abierto
Secondary Circuit Low|circuito secundario, valor bajo
Secondary Circuit High|circuito secundario, valor alto
Loss of Pressure|pérdida de presión
Charge Loss|pérdida de carga
Loss Of Synchronization|pérdida de sincronización
Overboost Condition|sobrealimentación excesiva
Underboost Condition|sobrealimentación insuficiente
Leak Detected (small leak)|fuga pequeña detectada
Leak Detected (very small leak)|fuga muy pequeña detectada
Leak Detected (gross leak)|fuga grande detectada
(MIL Request)|(petición de encender el testigo de avería)
Circuit (PRNDL Input)|circuito (entrada PRNDL)
Incorrect Gear Ratio|relación de marcha incorrecta
Differential Pressure Too Low|presión diferencial demasiado baja
Differential Pressure Too High|presión diferencial demasiado alta
Disconnected|desconectado
Slippage|deslizamiento
Stalled|calado
Ajar|entreabierto
Early|adelantado
Late|retrasado
"""


def _cargar(texto, campos):
    d = {}
    for linea in texto.strip().splitlines():
        partes = linea.split("|")
        d[partes[0]] = partes[1:] if campos > 1 else partes[1]
    return d


NOMBRES = {k: (v[0], v[1], v[2] == "1") for k, v in _cargar(_N, 3).items()}
ADJETIVOS = {k: (v[0], v[1], len(v) > 2 and v[2] == "pre") for k, v in _cargar(_A, 3).items()}
FALLOS = _cargar(_F, 1)
for _k, _v in list(FALLOS.items()):
    if "Circuit" in _k.split():
        for _l in "ABCDEFGH":
            FALLOS.setdefault(_k.replace("Circuit", "Circuit " + _l, 1), _v.replace("circuito", "circuito " + _l, 1))
    if _k.startswith(("Circuit/Open", "Control Circuit/Open")):
        for _l in "ABCDEFGH":
            FALLOS.setdefault(_k.replace("Circuit/Open", f"Circuit {_l}/Open"), _v.replace("circuito", "circuito " + _l, 1))
_MAX_N = max(len(k.split()) for k in list(NOMBRES) + list(ADJETIVOS))
_MAX_F = max(len(k.split()) for k in FALLOS)

_ART = {"m": "del", "f": "de la", "mp": "de los", "fp": "de las"}
_SUFIJO = re.compile(r'^([A-Z]|\d{1,2}|"[A-Z]"|\([+-]\)|U-V-W|[UVW]|X-Y-Z|X-Y|[XYZ]|[A-H]/[A-H]|[A-H]/[A-H]/[A-H]|\d/\d|\(\w+\))$')


def _unidades(tokens):
    """Componente -> lista de unidades [es, género, art, sufijo]; None si hay palabras desconocidas."""
    unidades, adj_pendientes, pre_sufijo = [], [], ""
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if _SUFIJO.match(t) and not any(" ".join(tokens[i:i + n]) in NOMBRES for n in range(1, 4)):
            t = t.strip('"')
            if unidades and not adj_pendientes:
                unidades[-1][3] += " " + t
            else:
                pre_sufijo += " " + t       # «A Camshaft…»: la letra va con lo que sigue
            i += 1
            continue
        for n in range(min(_MAX_N, len(tokens) - i), 0, -1):
            frase = " ".join(tokens[i:i + n])
            if frase in NOMBRES:
                es, g, art = NOMBRES[frase]
                pre, post = [], []
                for a in adj_pendientes:
                    m, f, es_pre = ADJETIVOS[a]
                    forma = f if g.startswith("f") else m
                    if g.endswith("p") and not forma.startswith(("de ", "del ", "antes ", "después ")):
                        forma = forma + ("es" if forma[-1] not in "aeiouáéó" else "s")
                    (pre if es_pre else post).append(forma)
                texto = " ".join(pre + [es] + post[::-1])
                unidades.append([texto, g, art, pre_sufijo])
                adj_pendientes, pre_sufijo = [], ""
                i += n
                break
            if frase in ADJETIVOS:
                adj_pendientes.append(frase)
                i += n
                break
        else:
            return None
    if adj_pendientes:
        return None
    return unidades


def _componente(texto, con_genero=False):
    tokens = texto.split()
    if not tokens:
        return ("", None) if con_genero else ""
    u = _unidades(tokens)
    if u is None:
        return (None, None) if con_genero else None
    partes = []
    nucleo_suf = ""
    al_final = not any(x[3] for x in u[:-1])
    for k, (es, g, art, suf) in enumerate(reversed(u)):
        if k == 0:
            # «Brake Pressure Sensor A» -> «Sensor de presión de frenado A»;
            # «Drive Motor A Phase Z» -> «Fase Z del motor de tracción A»
            if al_final:
                partes.append(es)
                nucleo_suf = suf
            else:
                partes.append(es + suf)
        else:
            partes.append((_ART[g] if art else "de") + " " + es + suf)
    texto = " ".join(partes) + nucleo_suf
    return (texto, u[-1][1]) if con_genero else texto


def _fallo(tokens):
    """Parte el final del título en fallos conocidos (de derecha a izquierda).

    Devuelve (índice donde empieza el fallo, lista de textos en español)."""
    fin, piezas = len(tokens), []
    while fin > 0:
        for n in range(min(_MAX_F, fin), 0, -1):
            frase = " ".join(tokens[fin - n:fin])
            if frase in FALLOS:
                piezas.insert(0, FALLOS[frase])
                fin -= n
                break
        else:
            break
        # letras sueltas dentro del fallo («Circuit A Low»): van con el circuito
        while fin > 0 and piezas and re.fullmatch(r"[A-H]", tokens[fin - 1]) and fin - 1 > 0 \
                and " ".join(tokens[max(0, fin - 2):fin - 1]) in ("Circuit", "Control Circuit"):
            piezas[0] = piezas[0] + " " + tokens[fin - 1]
            fin -= 1
    return fin, piezas


_POSICION = [
    (re.compile(r"\s*\(Bank (\d),? Sensor (\w) / Bank (\d),? Sensor (\w)\)"), "banco {0}, sensor {1} / banco {2}, sensor {3}"),
    (re.compile(r"\s*\(?\bBank\s?(\d),?\s+Sensor\s+([A-Z0-9])\)?"), "banco {0}, sensor {1}"),
    (re.compile(r"\s*\(Cam/Rotor/Injector\)"), "leva/rotor/inyector"),
    (re.compile(r"\s*\(?Bank (\d) or Single Sensor\)?"), "banco {0} o sensor único"),
    (re.compile(r"\s*\(?\bBank\s?(\d)\s+Unit\s+(\d)\)?"), "banco {0}, unidad {1}"),
    (re.compile(r"\s*\(?\bUnit\s+(\d)\)?$"), "unidad {0}"),
    (re.compile(r"\s*\(?\bBank\s?(\d)\s+Sensor\s+(\d)\)?"), "banco {0}, sensor {1}"),
    (re.compile(r"\s*\(?\bBank\s?(\d)\)?"), "banco {0}"),
]

_PLANTILLAS = [
    (r"Lost Communication With (.+)", "Sin comunicación con {el}"),
    (r"Invalid Data Received From (.+)", "Datos no válidos recibidos {del}"),
    (r"Software Incompatibility With (.+)", "Software incompatible con {el}"),
    (r"(.+) Incompatibility With (.+)", "{}: incompatible con {}"),
    (r"Excessive Time To Enter Closed Loop (.+)", "{}: tarda demasiado en entrar en lazo cerrado"),
    (r"Insufficient Coolant Temperature for Closed Loop Fuel Control", "Temperatura del refrigerante insuficiente para el control de combustible en lazo cerrado"),
    (r"(.+) Misfire Detected", "{}: fallos de encendido detectados"),
    (r"Random/Multiple Cylinder Misfire Detected", "Fallos de encendido aleatorios o en varios cilindros"),
    (r"(.+) Not Programmed", "{}: sin programar"),
    (r"Cold Start (.+)", "{} (en arranque en frío)"),
    (r"Alternative Fuel (.+)", "{} (combustible alternativo)"),
    (r"(.+) Requested MIL Illumination", "{}: solicita encender el testigo de avería (MIL)"),
    (r"(.+) During (.+)", "{} durante {}"),
    (r"(.+) Exceedence", "{}: superación de límites"),
    (r"(.+) Exceedance", "{}: superación de límites"),
    (r"Unable to Engage (.+)", "No se puede engranar {el}"),
    (r"Replace (.+)", "Sustituir {el}"),
    (r"(.+) / (.+) Correlation", "{}: correlación incorrecta con {}"),
    (r"(.+) Correlation", "{}: correlación incorrecta"),
]


_EL = {"m": "el", "f": "la", "mp": "los", "fp": "las"}
_DEL = {"m": "del", "f": "de la", "mp": "de los", "fp": "de las"}


def _con_articulo(t, tabla):
    """Componente con artículo («el módulo de control…»), o None."""
    texto, g = _componente(t, con_genero=True)
    if not texto:
        return None
    if texto[:2].isupper() and tabla is _EL:
        return "el " + texto
    if texto[:2].isupper():
        return "del " + texto
    return tabla[g] + " " + texto[0].lower() + texto[1:]


def _titulo(t):
    """Traducción de un título sin plantilla, o None."""
    posiciones = []
    for patron, fmt in _POSICION:
        def guardar(m):
            posiciones.append(fmt.format(*m.groups()))
            return ""
        t = patron.sub(guardar, t)
    t = t.strip()
    tokens = t.split()
    ini, piezas = _fallo(tokens)
    comp = _componente(" ".join(tokens[:ini]))
    if comp is None:
        return None
    if not comp:
        if not piezas:
            return None
        texto = ", ".join(piezas)
    else:
        texto = comp + (": " + ", ".join(piezas) if piezas else "")
    if posiciones:
        texto += " (" + ", ".join(posiciones) + ")"
    return texto


_LADOS = {"Front": "delante", "Rear": "detrás", "Left": "izquierda", "Right": "derecha", "Center": "centro"}
_LADO = re.compile(r"(?:\s+-)?\s+((?:Front|Rear)\s+(?:Left|Right|Center)|Left|Right|Center|Front|Rear)(?=$|\s+(?:Performance|Circuit|Stuck|Malfunction|Intermittent)\b)")


def traducir(titulo):
    """Título inglés de OBDex -> español, o None si no se sabe traducir entero."""
    titulo = titulo.strip()
    # posición (banco, sensor, unidad) y lado al final: se traducen aparte y van entre paréntesis
    posiciones = []
    for patron, fmt in _POSICION:
        m = patron.search(titulo)
        if m and (m.end() == len(titulo) or titulo[m.end():].lstrip().startswith("-") is False):
            pass
    m = _LADO.search(titulo)
    if m and len(titulo[:m.start()].split()) > 1:
        posiciones.append(", ".join(_LADOS[w] for w in m.group(1).split()))
        titulo = (titulo[:m.start()] + titulo[m.end():]).strip()
    for patron, fmt in _POSICION:
        def guardar(mm):
            posiciones.append(fmt.format(*mm.groups()))
            return ""
        titulo = patron.sub(guardar, titulo).strip()
    texto = _traducir(titulo)
    if texto is None:
        return None
    if posiciones:
        texto += " (" + ", ".join(posiciones) + ")"
    return texto


def _traducir(titulo):
    """Sin posiciones: partes con « - », plantillas o título normal."""
    # partes separadas por « - » («Fuel System Leak Detected - Large Leak»)
    m = re.fullmatch(r"Incorrect Shift from Gear (\d+)", titulo)
    if m:
        return f"Cambio incorrecto desde la marcha {m.group(1)}"
    if " - " in titulo and not re.search(r"Performance - Over", titulo):
        partes = [_traducir(p) for p in titulo.split(" - ")]
        if any(p is None for p in partes):
            return None
        return " - ".join(p[0].lower() + p[1:] if i and not p[:3].isupper() else p for i, p in enumerate(partes))
    for patron, fmt in _PLANTILLAS:
        m = re.fullmatch(patron, titulo)
        if m and ("{el}" in fmt or "{del}" in fmt):
            g = m.group(1)
            # posición al final («… Module - Right»)
            comp = _con_articulo(g, _EL if "{el}" in fmt else _DEL)
            if comp is None:
                return None
            texto = fmt.replace("{el}", comp).replace("{del}", comp)
            return texto[0].upper() + texto[1:]
        if m:
            grupos = [_titulo(g) for g in m.groups()]
            if any(g is None for g in grupos):
                return None
            grupos = [g if g[:2].isupper() else g[0].lower() + g[1:] for g in grupos]
            texto = fmt.format(*grupos)
            return texto[0].upper() + texto[1:]
    texto = _titulo(titulo)
    if texto is None:
        return None
    return texto[0].upper() + texto[1:]
