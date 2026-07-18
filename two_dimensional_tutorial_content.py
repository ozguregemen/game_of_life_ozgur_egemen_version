"""Curriculum and references for the contextual two-dimensional tutorial."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TutorialSection:
    """One ordered teaching point on a tutorial page."""

    title: str
    body: str


@dataclass(frozen=True)
class TutorialPage:
    """A tutorial page with an illustration kind and explanatory sections."""

    kicker: str
    title: str
    lead: str
    sections: tuple[TutorialSection, ...] = ()
    kind: str = "concepts"


@dataclass(frozen=True)
class TutorialSource:
    """A readable citation paired with an external destination."""

    category: str
    title: str
    detail: str
    url: str


@dataclass(frozen=True)
class ModeGuide:
    """The pages and sources displayed for exactly one active 2D mode."""

    name: str
    short_name: str
    pages: tuple[TutorialPage, ...]
    sources: tuple[TutorialSource, ...]


SCIENTIFIC_AMERICAN_LIFE = (
    "https://www.scientificamerican.com/article/mathematical-games-1970-10/"
)
NETLOGO_LIFE = "https://ccl.northwestern.edu/netlogo/models/Life"
LIFEWIKI_LIFE = "https://conwaylife.com/wiki/Conway%27s_Game_of_Life"
LIFEWIKI_IMMIGRATION = "https://conwaylife.com/wiki/Immigration"
IMMIGRATION_EVOLUTION = "https://arxiv.org/abs/2004.02720"
MULTICOLORED_LIFE = "https://conwaylife.com/ref/mniemiec/color.htm"
NETLOGO_BRAINS_BRAIN = "https://ccl.northwestern.edu/netlogo/models/Brian%27sBrain"
LIFEWIKI_BRAINS_BRAIN = "https://conwaylife.com/wiki/OCA%3ABrian%27s_Brain"
LANGTON_ORIGINAL = "https://doi.org/10.1016/0167-2789(86)90237-X"
LANGTON_COMPLEXITY = "https://arxiv.org/abs/nlin/0306022"
SCIENTIFIC_AMERICAN_WIREWORLD = (
    "https://www.scientificamerican.com/article/computer-recreations/"
)
QUINAPALUS_WIREWORLD = "https://www.quinapalus.com/wires2.html"
FISCH_CYCLIC = "https://doi.org/10.1016/0167-2789(90)90170-T"
CYCLIC_THRESHOLD = "https://arxiv.org/abs/patt-sol/9304001"


def _section(title: str, body: str) -> TutorialSection:
    return TutorialSection(title, body)


def _page(
    kicker: str,
    title: str,
    lead: str,
    kind: str,
    *sections: TutorialSection,
) -> TutorialPage:
    return TutorialPage(kicker, title, lead, tuple(sections), kind)


FOUNDATION_PAGES: tuple[TutorialPage, ...] = (
    _page(
        "2D FOUNDATIONS 1 - SPACE",
        "A cell sees only its local neighborhood",
        "Both visible axes are space. Pick one focus cell: it stores one state and can read only the nearby cells selected by the model's neighborhood.",
        "lattice",
        _section("The square in the middle", "The gold square is the focus cell whose next state is being calculated."),
        _section("The eight highlighted squares", "They form the Moore neighborhood used by every current 2D mode except the moving-agent interpretation of Langton's Ant."),
        _section("Everything farther away", "Distant cells cannot affect the focus cell in this generation. Information crosses the board through repeated local updates."),
        _section("State is not always life", "A state can mean alive, species A, firing, electron head, wire, a cyclic color, or any other discrete condition."),
    ),
    _page(
        "2D FOUNDATIONS 2 - SYNCHRONOUS TIME",
        "Read the old board, then commit together",
        "The visual uses a deliberately simple demo rule: every cell copies the state immediately to its left. All cells read generation t before any result is written.",
        "synchronous",
        _section("1. Freeze generation t", "Treat the current board as read-only. Every cell gets its evidence from this same snapshot."),
        _section("2. Calculate a separate next board", "The highlighted pattern shifts right because each destination copies its left neighbor; no partially updated cell can influence another calculation."),
        _section("3. Commit all results at once", "Only after every next state is known does generation t+1 replace generation t."),
        _section("4. Repeat", "The same two-phase operation creates every later generation. An in-place left-to-right loop would be a different system."),
    ),
    _page(
        "2D FOUNDATIONS 3 - BEHAVIOR",
        "Equal pictures can mean a period, not a mistake",
        "Repeated local updates can settle, alternate, move, disappear, or remain irregular. The examples below use Conway's Life only to name these common behaviors.",
        "behaviors",
        _section("Stable", "A still life has period 1: generation 0 and generation 1 are identical."),
        _section("Periodic", "A blinker has period 2: generation 0 becomes a different generation 1, then the rule reconstructs generation 0 at generation 2."),
        _section("Translating", "A spaceship repeats its shape at a shifted position, so shape period and motion must be considered together."),
        _section("Transient", "A pattern may change for a while and then vanish or stabilize. One frame cannot reveal its long-term class."),
    ),
    _page(
        "2D FOUNDATIONS 4 - MODEL",
        "Four choices define a cellular automaton",
        "A screenshot does not fully specify an experiment. Record the state alphabet, neighborhood, transition function, and boundary or initial condition.",
        "model",
        _section("State alphabet", "Conway has two states, Brian's Brain three, Wireworld four, and this Cyclic CA eight."),
        _section("Neighborhood", "Moore means the eight surrounding cells. Other automata can use four faces, longer ranges, weights, or an agent."),
        _section("Transition function", "The rule maps the current local evidence to the focus cell's next state."),
        _section("Boundary and seed", "Board size, edge behavior, starting pattern, and agent direction are experimental parameters, not decoration."),
    ),
    _page(
        "2D FOUNDATIONS 5 - EDGES",
        "The edge changes what a border cell can see",
        "This application's 2D board is finite and fixed: beyond the visible edge is inactive background. A wrapped world would connect opposite edges and can produce a different result.",
        "boundaries",
        _section("Fixed boundary - used here", "A corner cell has only three in-bounds neighbors. Nothing enters from the opposite side."),
        _section("Wrapped boundary - comparison", "In a torus, leaving the right edge re-enters on the left and every cell still has eight neighbors."),
        _section("Why record it", "A glider can leave a fixed board but return on a wrapped board. Identical rules and seeds can therefore diverge."),
        _section("Keep seeds away from edges", "When comparing local rules, begin near the center unless boundary interaction is the subject of the experiment."),
    ),
    _page(
        "2D FOUNDATIONS 6 - LAB WORKFLOW",
        "Ask one question and preserve the evidence",
        "Treat a run as a reproducible experiment: prepare a known state, change one variable, inspect time rather than one frame, and save the context with the result.",
        "laboratory",
        _section("Prepare", "Pause, clear the board, then draw or load a verified mode-specific pattern."),
        _section("Run", "Use Space for continuous time, N for one generation, and the timeline for controlled review."),
        _section("Measure", "Population, density, entropy, change rate, periods, species shares, or state diversity answer different questions."),
        _section("Save and compare", "Store the session or profile, then export images, animation, CSV metrics, or experiment JSON."),
    ),
)


LIFE_PAGES = (
    _page(
        "LIFE-LIKE 1 - IDENTITY",
        "Meet Conway's Game of Life",
        "John Conway devised Life in 1970, and Martin Gardner introduced it publicly that October. It is a zero-player system: after the seed is placed, the rule alone evolves the board.",
        "mode_identity",
        _section("Creator", "John Horton Conway, 1970."),
        _section("Public introduction", "Martin Gardner's Scientific American column made the game widely known."),
        _section("Family", "Two states, eight Moore neighbors, and an outer-totalistic birth/survival rule."),
        _section("This app", "The Rule control also exposes HighLife, Day & Night, and Seeds using the same B/S notation."),
    ),
    _page(
        "LIFE-LIKE 2 - WHAT IS COUNTED",
        "Count live neighbors around the focus cell",
        "The center cell does not count itself. Inspect the eight surrounding squares and count only live cells; the center's current state decides whether the birth or survival table applies.",
        "mode_states",
        _section("Dead focus cell", "Use the B part of the rulestring to decide whether it is born."),
        _section("Live focus cell", "Use the S part to decide whether it survives."),
        _section("Moore neighborhood", "Diagonal and orthogonal neighbors count equally."),
        _section("Current rule", "Conway is B3/S23: birth on 3, survival on 2 or 3."),
    ),
    _page(
        "LIFE-LIKE 3 - BIRTH",
        "Why a dead cell becomes alive",
        "Follow the highlighted center from old board to new board. In Conway's B3 rule, exactly three live neighbors create a birth.",
        "mode_rule_primary",
        _section("Read", "The center is currently dead."),
        _section("Count", "Exactly three of its eight neighbors are alive."),
        _section("Match B3", "Three appears in the birth list, so the next center state is alive."),
        _section("Other counts", "With 0, 1, 2, or 4-8 neighbors, a dead Conway cell remains dead."),
    ),
    _page(
        "LIFE-LIKE 4 - SURVIVAL AND DEATH",
        "Why a live cell survives or dies",
        "A live Conway cell survives only with two or three live neighbors. Too few is isolation; too many is crowding. Both produce a dead cell in the next generation.",
        "mode_rule_secondary",
        _section("Two neighbors", "The live center survives because 2 is in S23."),
        _section("Three neighbors", "The live center also survives because 3 is in S23."),
        _section("Zero or one", "The cell dies from underpopulation."),
        _section("Four through eight", "The cell dies from overpopulation."),
    ),
    _page(
        "LIFE-LIKE 5 - PLAY AND OBSERVE",
        "Use named patterns as controlled experiments",
        "Still lifes, oscillators, spaceships, guns, and methuselahs reveal different consequences of the same local rule.",
        "mode_experiment",
        _section("Still lifes", "Blocks and beehives test stability."),
        _section("Oscillators", "Blinkers and pulsars make period directly visible."),
        _section("Spaceships", "Gliders repeat after translating across the board."),
        _section("Long transients", "R-pentomino and similar seeds show why many generations and a timeline matter."),
    ),
    _page("LIFE-LIKE 6 - SOURCES", "Continue with reliable references", "Only references for the active Life-like mode appear here.", "mode_sources"),
)


IMMIGRATION_PAGES = (
    _page(
        "IMMIGRATION 1 - IDENTITY",
        "Conway geometry with two competing lineages",
        "Don Woods created the Immigration Game in 1971. Ignoring color, its occupied cells evolve exactly as Conway Life; color records ancestry at births.",
        "mode_identity",
        _section("Creator", "Don Woods, 1971."),
        _section("Three board states", "Empty, species A, and species B."),
        _section("Symmetric species", "A and B obey the same survival and birth geometry."),
        _section("Competition", "A newborn inherits the majority color of its three parents."),
    ),
    _page(
        "IMMIGRATION 2 - WHAT IS COUNTED",
        "Count A and B together before considering color",
        "For life-or-death decisions, both species are simply alive. A blue neighbor and an orange neighbor each contribute one to the Conway B3/S23 count.",
        "mode_states",
        _section("Empty", "No population and no species."),
        _section("Species A", "Alive; counts as one live neighbor."),
        _section("Species B", "Alive; also counts as one live neighbor."),
        _section("Two-stage reasoning", "First decide occupancy with B3/S23, then color only a newborn."),
    ),
    _page(
        "IMMIGRATION 3 - OCCUPANCY",
        "First apply Conway's birth and survival counts",
        "The highlighted dead center has three live parents in total, so it is born. Their colors do not alter whether the birth occurs.",
        "mode_rule_primary",
        _section("Combine species", "A + B + B is a total of three live neighbors."),
        _section("Apply B3", "The empty center becomes occupied because the total equals three."),
        _section("Survivors", "An existing A or B survives with two or three total live neighbors."),
        _section("Deaths", "Underpopulation and overpopulation ignore species color."),
    ),
    _page(
        "IMMIGRATION 4 - INHERITANCE",
        "Then assign the newborn's majority species",
        "A Conway birth always has exactly three parents, so there cannot be a color tie: A+A+B produces A, while A+B+B produces B.",
        "mode_rule_secondary",
        _section("Two A parents", "The newborn is species A."),
        _section("Two B parents", "The newborn is species B."),
        _section("Existing cells", "A survivor keeps its old species; it is never recolored by its neighbors."),
        _section("No direct conquest", "Territory changes color only when deaths create empty space and later births refill it."),
    ),
    _page(
        "IMMIGRATION 5 - LINEAGE THROUGH TIME",
        "Separate ancestry from occupied geometry",
        "Two runs with the same occupied seed but different colors have the same live/dead silhouette. Only the lineage map and species census differ.",
        "mode_process",
        _section("Geometry layer", "Treat A and B as one live state to predict births and deaths."),
        _section("Lineage layer", "Inspect the three parents only when a new cell is born."),
        _section("Fair starts", "Use balanced populations or mirrored seeds before interpreting a winner."),
        _section("Accessible reading", "The Colorblind theme distinguishes species with shape as well as hue."),
    ),
    _page(
        "IMMIGRATION 6 - PLAY AND MEASURE",
        "Watch collisions, births, and species share",
        "Use matched seeds to ask whether ancestry or collision geometry determines the final census.",
        "mode_experiment",
        _section("Start balanced", "Place comparable A and B populations."),
        _section("Step through births", "Use N to verify which three parents colored a newborn."),
        _section("Read the census", "Track both species counts and shares, not population alone."),
        _section("Repeat", "Swap colors while preserving geometry to test symmetry."),
    ),
    _page("IMMIGRATION 7 - SOURCES", "Continue with reliable references", "Only references for the active Immigration Game appear here.", "mode_sources"),
)


BRIANS_BRAIN_PAGES = (
    _page(
        "BRIAN'S BRAIN 1 - IDENTITY",
        "An excitable three-state automaton",
        "Brian Silverman devised this Generations automaton. A mandatory dying state gives each firing event a direction and creates waves, ships, and temporary wakes.",
        "mode_identity",
        _section("Creator", "Brian Silverman."),
        _section("Three phases", "Off, firing, and dying/refractory."),
        _section("Neighborhood", "Eight Moore neighbors update synchronously."),
        _section("Interpretation", "The neural vocabulary is a metaphor, not a biological brain model."),
    ),
    _page(
        "BRIAN'S BRAIN 2 - STATE CYCLE",
        "Every firing cell must cool down",
        "Only off cells make a neighbor-count decision. Firing and dying cells follow a fixed one-generation phase sequence.",
        "mode_states",
        _section("Off", "Ready to fire if exactly two neighboring cells are firing."),
        _section("Firing", "Active for one generation and counted by nearby off cells."),
        _section("Dying", "Refractory for one generation and not counted as firing."),
        _section("Return", "Dying always becomes off on the next update."),
    ),
    _page(
        "BRIAN'S BRAIN 3 - EXCITATION",
        "Why an off cell starts firing",
        "The highlighted off center sees exactly two firing neighbors. That count activates it in the next generation; one or three firing neighbors would not.",
        "mode_rule_primary",
        _section("Read only firing neighbors", "Dying cells do not contribute to the count."),
        _section("Count exactly two", "The birth condition is neither at least two nor two or three."),
        _section("Activate", "The off center becomes firing in the next generation."),
        _section("Other counts", "The center remains off."),
    ),
    _page(
        "BRIAN'S BRAIN 4 - REFRACTORY PHASE",
        "Why a signal leaves a temporary trail",
        "Firing becomes dying unconditionally, then dying becomes off unconditionally. The old firing site cannot immediately fire again.",
        "mode_rule_secondary",
        _section("Generation t", "The cell is firing and can excite neighbors."),
        _section("Generation t+1", "It is dying and ignored by firing-neighbor counts."),
        _section("Generation t+2", "It returns to off and can be excited again."),
        _section("Direction", "New firing appears ahead while refractory cells remain behind, making motion readable."),
    ),
    _page(
        "BRIAN'S BRAIN 5 - FOLLOW A WAVE",
        "Read the leading edge and the wake separately",
        "A moving pattern is not one object being translated by the program. New firing cells are created at the front while older cells pass through dying to off behind it.",
        "mode_process",
        _section("Front", "Cyan firing cells are the only cells that can excite the next front."),
        _section("Wake", "Purple dying cells record where the front was one generation ago."),
        _section("Recovered space", "After another step the wake becomes off again."),
        _section("Use stepping", "Advance with N to keep the two phases visually separate."),
    ),
    _page(
        "BRIAN'S BRAIN 6 - PLAY AND OBSERVE",
        "Look for ships, rakes, and expanding fronts",
        "Verified sparse seeds are easier to interpret than a dense random field.",
        "mode_experiment",
        _section("Begin sparse", "Dense starts quickly become visually noisy."),
        _section("Follow direction", "Firing leads and dying trails."),
        _section("Measure activity", "Track firing population separately from total non-off cells."),
        _section("Compare seeds", "Rotate or mirror a seed to test directional symmetry."),
    ),
    _page("BRIAN'S BRAIN 7 - SOURCES", "Continue with reliable references", "Only references for Brian's Brain appear here.", "mode_sources"),
)


LANGTON_PAGES = (
    _page(
        "LANGTON'S ANT 1 - IDENTITY",
        "A moving agent writes on a two-color world",
        "Christopher Langton introduced the virtual ant in 1986. Unlike the other modes, it updates one visited square and moves one agent per step rather than updating the whole grid together.",
        "mode_identity",
        _section("Creator", "Christopher G. Langton, 1986."),
        _section("Board memory", "Every square stores white or black."),
        _section("Agent memory", "The ant stores a position and one of four headings."),
        _section("Sequential system", "Exactly one square and one ant position change during a step."),
    ),
    _page(
        "LANGTON'S ANT 2 - WHAT STORES STATE",
        "Read the tile under the arrow",
        "The board color and ant direction are both necessary. The same colored board can evolve differently when the ant starts in another position or heading.",
        "mode_states",
        _section("White tile", "Commands a right turn."),
        _section("Black tile", "Commands a left turn."),
        _section("Arrow", "Shows the ant's current heading before it turns."),
        _section("Operation order", "Read color, turn, flip the old tile, then move forward."),
    ),
    _page(
        "LANGTON'S ANT 3 - WHITE TILE STEP",
        "White means turn right, flip, then move",
        "Follow the four pictures from left to right. The ant reads white, rotates 90 degrees right, paints the tile black, and moves one square in its new direction.",
        "mode_rule_primary",
        _section("Read", "The tile under the ant is white."),
        _section("Turn", "Rotate right relative to the current heading."),
        _section("Flip", "The tile just visited becomes black."),
        _section("Move", "Advance one square after turning and painting."),
    ),
    _page(
        "LANGTON'S ANT 4 - BLACK TILE STEP",
        "Black means turn left, flip, then move",
        "The mirror instruction applies on black: rotate 90 degrees left, paint the old tile white, and move forward in the new heading.",
        "mode_rule_secondary",
        _section("Read", "The tile under the ant is black."),
        _section("Turn", "Rotate left relative to the current heading."),
        _section("Flip", "The tile just visited becomes white."),
        _section("Move", "Advance one square after the flip."),
    ),
    _page(
        "LANGTON'S ANT 5 - MULTIPLE STEPS",
        "The next instruction is written by earlier visits",
        "A short trace shows the ant repeatedly reading, turning, flipping, and moving. Revisiting a square encounters its changed color and can reverse the later route.",
        "mode_process",
        _section("One step at a time", "Only the tile the ant leaves is flipped."),
        _section("The grid is memory", "Earlier visits alter instructions for future visits."),
        _section("Irregular transient", "A blank board usually produces a long, seemingly disordered path."),
        _section("Highway", "A repeating 104-step construction can eventually translate diagonally."),
    ),
    _page(
        "LANGTON'S ANT 6 - PLAY AND OBSERVE",
        "Vary position, direction, and initial black tiles",
        "The finite board stops the ant when it leaves the edge, so start near the center for long runs.",
        "mode_experiment",
        _section("Place the ant", "Shift-click chooses its position and heading controls define direction."),
        _section("Edit the board", "Draw black cells to alter the ant's future instructions."),
        _section("Step carefully", "Use N to verify the read-turn-flip-move order."),
        _section("Record the transient", "Compare highway onset time and visited area across seeds."),
    ),
    _page("LANGTON'S ANT 7 - SOURCES", "Continue with reliable references", "Only references for Langton's Ant appear here.", "mode_sources"),
)


WIREWORLD_PAGES = (
    _page(
        "WIREWORLD 1 - IDENTITY",
        "A cellular automaton for digital circuits",
        "Brian Silverman introduced Wireworld in 1987. Conductors provide fixed circuit geometry while electron heads and tails propagate signals through it.",
        "mode_identity",
        _section("Creator", "Brian Silverman, presented in Scientific American in 1987."),
        _section("Four states", "Empty, electron head, electron tail, and conductor."),
        _section("Circuit blueprint", "Conductor cells define wires, junctions, clocks, diodes, and gates."),
        _section("Synchronous update", "Every cell reads the previous generation before changing."),
    ),
    _page(
        "WIREWORLD 2 - FOUR STATES",
        "Separate circuit geometry from the moving signal",
        "A conductor is a possible path, not an active signal. A signal is a two-cell pulse: a head followed by a tail moving through conductor cells.",
        "mode_states",
        _section("Empty", "Permanent background unless you edit it."),
        _section("Electron head", "The leading edge of a pulse; it becomes a tail next."),
        _section("Electron tail", "The refractory wake; it becomes conductor next."),
        _section("Conductor", "Becomes a head only when one or two neighboring heads reach it."),
    ),
    _page(
        "WIREWORLD 3 - SIGNAL MOTION",
        "A pulse advances because cells change phase",
        "Follow the same wire through four generations. The old head becomes tail, the old tail restores conductor, and the conductor ahead becomes the new head.",
        "mode_rule_primary",
        _section("Head to tail", "Every electron head becomes an electron tail."),
        _section("Tail to conductor", "Every electron tail becomes ordinary conductor."),
        _section("Conductor ahead", "It becomes the new head when it sees one or two heads."),
        _section("Apparent motion", "No electron object is moved; the state sequence recreates the pulse one cell ahead."),
    ),
    _page(
        "WIREWORLD 4 - SIGNAL RECEPTION",
        "Only one or two neighboring heads activate a conductor",
        "Compare four local neighborhoods. A conductor with zero or three head neighbors stays conductor; exactly one or two makes it a head next generation.",
        "mode_rule_secondary",
        _section("Zero heads", "No incoming signal, so the conductor remains conductor."),
        _section("One head", "The signal propagates into the conductor."),
        _section("Two heads", "The conductor also becomes a head, enabling junction logic."),
        _section("Three or more", "Crowded input is suppressed and the conductor remains conductor."),
    ),
    _page(
        "WIREWORLD 5 - FROM WIRES TO LOGIC",
        "Geometry controls where pulses meet",
        "Corners route a pulse, junctions combine paths, and carefully spaced conductor cells suppress or admit signals. That geometry implements diodes and Boolean gates.",
        "mode_process",
        _section("Wire", "A one-cell-wide conductor path carries a head-tail pulse."),
        _section("Junction", "Multiple routes change the number and timing of neighboring heads."),
        _section("Logic gate", "OR, XOR, AND-NOT, and related gates encode truth conditions in pulse arrival."),
        _section("Timing", "A valid shape can still fail when pulses reach a junction in the wrong generations."),
    ),
    _page(
        "WIREWORLD 6 - BUILD A RUNNABLE CIRCUIT",
        "Place geometry first, then inject a pulse",
        "Use verified patterns for gates and add electron heads only at their intended inputs. Step through the first few generations before running at full speed.",
        "mode_application",
        _section("1. Place conductor", "Build or load the wire, diode, clock, gate, or adder geometry."),
        _section("2. Add a pulse", "Place a head with a tail immediately behind it in the desired direction."),
        _section("3. Step", "Verify that the pulse remains on the conductor and reaches each junction at the expected time."),
        _section("4. Read outputs", "Presence or absence of a pulse at an output wire represents the circuit result."),
    ),
    _page(
        "WIREWORLD 7 - PLAY AND MEASURE",
        "Test one circuit claim at a time",
        "Run every input combination for a logic gate and record whether each output emits a pulse.",
        "mode_experiment",
        _section("Begin with a diode", "Confirm one-way behavior before combining gates."),
        _section("Truth table", "Test 00, 01, 10, and 11 for two-input logic."),
        _section("Inspect timing", "Pause around junctions and use the timeline to identify collisions."),
        _section("Scale gradually", "Combine verified subcircuits into latches, clocks, and adders."),
    ),
    _page("WIREWORLD 8 - SOURCES", "Continue with reliable references", "Only references for Wireworld appear here.", "mode_sources"),
)


CYCLIC_PAGES = (
    _page(
        "CYCLIC CA 1 - IDENTITY",
        "A repeating color cycle creates traveling fronts",
        "Robert Fisch studied cyclic cellular automata in 1990. Every state has one successor, and local successor pressure makes cells advance around the cycle.",
        "mode_identity",
        _section("Rule family", "Deterministic cyclic cellular automata."),
        _section("Eight states here", "0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 0."),
        _section("Local geometry", "Eight Moore neighbors are counted synchronously."),
        _section("Threshold variant", "A cell advances only when enough neighbors already hold its successor state."),
    ),
    _page(
        "CYCLIC CA 2 - STATE RING",
        "Every color follows exactly one successor",
        "The state ring wraps after the last color. A state-7 cell seeks state 0, not state 8; colors are labels for discrete states, not blended values.",
        "mode_states",
        _section("Current state s", "Identify the focus cell's present state."),
        _section("Successor", "Compute (s + 1) modulo 8."),
        _section("Ignore other colors", "Only neighbors already in the successor state contribute to this update."),
        _section("Wrap", "State 7 advances to state 0 when the threshold is met."),
    ),
    _page(
        "CYCLIC CA 3 - COUNT THE SUCCESSOR",
        "Why a cell advances one color",
        "The highlighted state-3 center seeks state 4. Count only state-4 neighbors; when the configured threshold is reached, the next center state becomes 4.",
        "mode_rule_primary",
        _section("Find the target", "For state 3, the only target is successor state 4."),
        _section("Count locally", "Inspect all eight Moore neighbors but count only target-colored cells."),
        _section("Reach threshold", "At or above the threshold, advance exactly one state."),
        _section("No skipping", "A cell never jumps directly from state 3 to 5 or another visible neighbor color."),
    ),
    _page(
        "CYCLIC CA 4 - HOLD OR ADVANCE",
        "The threshold separates resistance from invasion",
        "Two otherwise identical focus cells can differ only in successor count: below threshold the state holds; at threshold it advances.",
        "mode_rule_secondary",
        _section("Below threshold", "The focus cell keeps its current state."),
        _section("At or above threshold", "The focus cell advances to its successor."),
        _section("Lower threshold", "Fronts spread easily and activity is usually high."),
        _section("Higher threshold", "Regions resist invasion and can freeze into large domains."),
    ),
    _page(
        "CYCLIC CA 5 - TRAVELING FRONTS",
        "Each color is chased by its predecessor",
        "A boundary moves because cells on one side see enough successor-colored neighbors on the other. Curved fronts can organize into rotating spiral cores.",
        "mode_process",
        _section("Front", "The narrow boundary is where most state changes occur."),
        _section("Wake", "After advancing, a cell becomes the successor target for the state behind it."),
        _section("Cycle", "Repeated invasion produces ordered color bands rather than one permanent winner."),
        _section("Spiral core", "Curved fronts can rotate around a persistent organizing center."),
    ),
    _page(
        "CYCLIC CA 6 - PLAY AND MEASURE",
        "Compare thresholds with the same random seed",
        "Change only one parameter and compare equal-duration runs to separate threshold effects from chance.",
        "mode_experiment",
        _section("Randomize evenly", "Seed all eight states to expose cyclic competition."),
        _section("Sweep threshold", "Keep the seed fixed while changing threshold."),
        _section("Measure organization", "Track entropy, change rate, diversity, and dominant share."),
        _section("Inspect fronts", "Use N and the timeline to follow one boundary through the cycle."),
    ),
    _page("CYCLIC CA 7 - SOURCES", "Continue with reliable references", "Only references for the active Cyclic CA appear here.", "mode_sources"),
)


MODE_GUIDES: dict[str, ModeGuide] = {
    "life": ModeGuide(
        "Life-like",
        "Life-like",
        LIFE_PAGES,
        (
            TutorialSource("ORIGINAL INTRODUCTION", "Gardner (1970) - Mathematical Games", "The Scientific American column that introduced Conway's Life publicly.", SCIENTIFIC_AMERICAN_LIFE),
            TutorialSource("TEACHING MODEL", "NetLogo Models Library - Life", "A concise explanation of the board, rules, experiments, and references.", NETLOGO_LIFE),
            TutorialSource("PATTERN ENCYCLOPEDIA", "LifeWiki - Conway's Game of Life", "Rules, history, terminology, and the modern pattern catalogue.", LIFEWIKI_LIFE),
        ),
    ),
    "immigration": ModeGuide(
        "Immigration Game",
        "Immigration",
        IMMIGRATION_PAGES,
        (
            TutorialSource("HISTORY & RESEARCH", "Conditions for Open-Ended Evolution in Immigration Games", "A modern paper identifying Don Woods's 1971 game and studying competitive evolution.", IMMIGRATION_EVOLUTION),
            TutorialSource("RULE OVERVIEW", "LifeWiki - Immigration", "A concise overview of the two-live-state majority-birth rule.", LIFEWIKI_IMMIGRATION),
            TutorialSource("COLOR SYSTEM", "Multi-colored Life - Immigration", "Detailed notes on the two-color rule and its two-player origin.", MULTICOLORED_LIFE),
        ),
    ),
    "brians_brain": ModeGuide(
        "Brian's Brain",
        "Brian's Brain",
        BRIANS_BRAIN_PAGES,
        (
            TutorialSource("TEACHING MODEL", "NetLogo Models Library - Brian's Brain", "Rules, experiments, and credits from Northwestern's educational model library.", NETLOGO_BRAINS_BRAIN),
            TutorialSource("RULE ENCYCLOPEDIA", "LifeWiki - Brian's Brain", "Generations notation, history, behavior, and known patterns.", LIFEWIKI_BRAINS_BRAIN),
        ),
    ),
    "langtons_ant": ModeGuide(
        "Langton's Ant",
        "Langton's Ant",
        LANGTON_PAGES,
        (
            TutorialSource("ORIGINAL PAPER", "Langton (1986) - Studying Artificial Life with Cellular Automata", "The Physica D paper introducing the ant in the context of artificial life.", LANGTON_ORIGINAL),
            TutorialSource("LONG-TERM ANALYSIS", "Gajardo et al. - Complexity of Langton's Ant", "A mathematical study of the ant's dynamics and complexity.", LANGTON_COMPLEXITY),
        ),
    ),
    "wireworld": ModeGuide(
        "Wireworld",
        "Wireworld",
        WIREWORLD_PAGES,
        (
            TutorialSource("ORIGINAL INTRODUCTION", "Dewdney (1987) - Computer Recreations", "The Scientific American article that presented Wireworld and related automata.", SCIENTIFIC_AMERICAN_WIREWORLD),
            TutorialSource("CIRCUIT TUTORIAL", "Quinapalus - Wireworld", "A visual progression from signals through diodes and Boolean logic circuits.", QUINAPALUS_WIREWORLD),
        ),
    ),
    "cyclic_automaton": ModeGuide(
        "Cyclic Cellular Automaton",
        "Cyclic CA",
        CYCLIC_PAGES,
        (
            TutorialSource("FOUNDATIONAL PAPER", "Fisch (1990) - Cyclic Cellular Automata and Related Processes", "Defines the deterministic cyclic process and relates it to cyclic particle systems.", FISCH_CYCLIC),
            TutorialSource("THRESHOLD STUDY", "Fisch, Gravner & Griffeath - Threshold-Range Scaling", "Research on contact thresholds and excitable cellular-automaton phase behavior.", CYCLIC_THRESHOLD),
        ),
    ),
}


def validate_curriculum() -> None:
    """Raise a clear error if the static curriculum is internally inconsistent."""
    if len(FOUNDATION_PAGES) < 5:
        raise ValueError("The 2D foundation curriculum is unexpectedly short.")
    for mode, guide in MODE_GUIDES.items():
        if len(guide.pages) < 6:
            raise ValueError(f"The {mode} guide does not explain the mode fully.")
        if guide.pages[-1].kind != "mode_sources":
            raise ValueError(f"The {mode} guide must finish with its sources.")
        if not guide.sources:
            raise ValueError(f"The {mode} guide must contain at least one source.")
        if any(not source.url.startswith("https://") for source in guide.sources):
            raise ValueError(f"The {mode} guide contains an unsafe source URL.")


validate_curriculum()
