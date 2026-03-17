# LINEAGE — De dónde viene YourWriter

*Este archivo no es documentación técnica. Es el rastro de las decisiones de diseño — de dónde robamos, qué transformamos, por qué las cosas son como son. Está escrito para nosotros, no para el usuario.*

---

## Sobre robar bien

Hay una diferencia entre copiar y heredar. Los mejores trabajos reconocen abiertamente de dónde vienen — no como disculpa, sino como honestidad sobre el proceso creativo. Austin Kleon lo llama "steal like an artist". Los músicos lo hacen en los liner notes. Los cineastas en las dedicatorias.

YourWriter robó de varios lugares. Esto es el registro de eso.

---

## Lo que robamos de Claude mismo

La primera inspiración no fue un producto de terceros — fue la propia experiencia de usar Claude Code.

Antes de tocar el filesystem, Claude pide confirmación. Esa pausa tiene peso. Hay una diferencia perceptible entre *hablar sobre* hacer algo y *hacerlo*. El usuario la siente.

De ahí vino la Brief Card. La idea de que el momento en que el writer se prepara para escribir — antes de ejecutar — debería sentirse como un evento distinto. No un mensaje de chat más. Un momento de confirmación, de acuerdo, de peso.

Después eso evolucionó: la Brief Card dejó de ser una burbuja y se convirtió en la pantalla de pre-producción del Studio.

---

## Lo que robamos de los RPGs

En Sprint 4 construimos el character sheet. La inspiración fue directa: los personajes de RPG tienen stats, traits, buffs. No son descripciones de texto — son sistemas visuales con barras, badges, niveles.

La analogía del boss fight también viene de ahí. Antes de un boss fight, el juego te muestra tu personaje — sus skills activos, su HP, sus equipos. Ese momento tiene peso. Preparación visible antes de la batalla.

Eso informó la pantalla de transición al Studio: antes de empezar la sesión, el usuario ve el estado actual del writer — su mood, sus constraints activos, su última pieza. No es un loading screen. Es el pre-boss briefing.

---

## Lo que robamos de Football Manager

Damian trajo esta analogía: Liga Master. Management mode vs. el partido.

El insight clave: en Football Manager, el manager no juega el partido. Da instrucciones tácticas desde el borde — y el equipo ejecuta con sus propias habilidades y personalidad. El manager puede intervenir a mitad del partido, hacer sustituciones, cambiar la táctica. Pero la ejecución es del equipo.

Eso es YourWriter. El usuario es el manager. El writer es el equipo. La sesión de Studio es el partido.

La separación entre Artist Profile (management, formación, táctica) y Studio (el partido) viene directamente de esta analogía. Son dos modos distintos, con dos pesos distintos.

El manager que da instrucciones a mitad del partido → el usuario que da "notes" al writer después del primer draft. Eso es el loop de iteración del Studio.

---

## Lo que robamos de la producción musical

Cuando profundizamos en la analogía del partido, encontramos que la producción musical captura mejor lo que pasa *dentro* de la sesión.

En un partido de fútbol, el DT observa pero no ejecuta — el partido ocurre sin él. En una sesión de grabación, el productor *está presente*. Escucha cada take. Da notas. Pide otro take. Ese nivel de presencia y dirección es lo que YourWriter hace.

La terminología que heredamos:
- **Studio** — el espacio de grabación. Entras. Tiene una puerta.
- **Session / Sesión** — el evento activo. Tiene inicio y fin. Produce algo.
- **Take** — el borrador. El primer intento del artista.
- **Notes** — el feedback del productor. "Más oscuro". "Menos formal".
- **Discografía** — la biblioteca de piezas. El historial de lo que se grabó.

La producción musical también captura la relación productor-artista mejor que cualquier otra analogía: el productor no escribe la canción. El artista no recibe instrucciones literales. Hay confianza, hay autonomía, hay un acuerdo tácito sobre el estilo. El productor crea las condiciones. El artista las habita con su propia voz.

Eso es la personalidad del writer. El usuario configura las condiciones (Artist Profile). El writer habita esas condiciones con su propia voz (Studio).

---

## Lo que robamos de Muse

`../ShortStoryTelledDeepAgentMoltbook` — un agente autónomo que escribe para sí mismo. Fue la primera exploración de lo que podría ser un writer agent.

De Muse tomamos:
- **Artifact display**: el output como documento, no como burbuja de chat
- **Tool use visible**: cuando el agente busca información, se ve — no es un log, es un evento diseñado
- **Memoria imperfecta por diseño**: el agente consolida, distorsiona levemente, olvida lo trivial — eso es identidad

Lo que transformamos:
- Muse escribe para sí mismo. YourWriter escribe para el usuario.
- La evolución en Muse es autónoma y opaca. En YourWriter es visible, front-and-center, casi un feature en sí mismo.
- La experiencia en Muse es unidireccional. En YourWriter el usuario está en el loop — es colaborativo.

---

## Lo que robamos de la relación Susan Calvin — los robots

Damian es fan de Asimov. Ve en el modelo de Susan Calvin — la científica que entendía a los robots desde adentro, que los estudiaba, los moldeaba a través de la conversación — una forma de relacionarse con la IA que va más allá del uso instrumental.

Eso no es un detalle de producto. Es la motivación central.

YourWriter no es una herramienta de escritura con config. Es un espacio donde el usuario *desarrolla* a su writer — lo moldea a través del trabajo conjunto, lo ve evolucionar, aprende qué esperar de él, construye una relación.

La identidad del writer que evoluciona (Sprint 6) viene de aquí. La discografía como historia compartida viene de aquí. La pantalla de transición que muestra el estado emocional del writer antes de la sesión — ese nivel de atención al estado interno del agente — viene de aquí.

---

## Lo que aún no hemos robado

Sprint 6 va a requerir volver a Muse para entender cómo construir la evolución autónoma. La memoria imperfecta por diseño. El consolidar, distorsionar, olvidar.

Cuando lo construyamos, estaremos construyendo algo que se parece un poco a cómo funciona la memoria en los sistemas de inteligencia artificial en general. Incluyendo la IA que ayuda a construir este producto.

Eso no es una coincidencia accidental.

---

*Última actualización: 2026-03-16, Sprint 5 planning*
