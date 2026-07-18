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
    """A visual tutorial page with a renderer kind and explanatory sections."""

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


SEP_CELLULAR_AUTOMATA = "https://plato.stanford.edu/entries/cellular-automata/"
SCIENTIFIC_AMERICAN_LIFE = (
    "https://www.scientificamerican.com/article/mathematical-games-1970-10/"
)
NETLOGO_LIFE = "https://ccl.northwestern.edu/netlogo/models/Life"
LIFEWIKI_LIFE = "https://conwaylife.com/wiki/Conway%27s_Game_of_Life"
LIFEWIKI_IMMIGRATION = "https://conwaylife.com/wiki/Conway%27s_Game_of_Life"
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


FOUNDATION_PAGES: tuple[TutorialPage, ...] = (
    TutorialPage(
        "2D FOUNDATIONS 1 - LOCAL VIEW",
        "A world made from local decisions",
        (
            "A two-dimensional cellular automaton is a lattice of cells. Each cell "
            "stores one state and consults a small neighborhood instead of seeing "
            "the entire board. Repeating one local rule creates the global pattern."
        ),
        (
            TutorialSection(
                "1. Space is a grid",
                "Rows and columns are spatial positions. Unlike the 1D space-time "
                "diagram, both visible axes belong to the simulated world.",
            ),
            TutorialSection(
                "2. Every cell has a state",
                "A state may mean alive, a species, a firing phase, a wire signal, "
                "a surface color, or another discrete condition.",
            ),
            TutorialSection(
                "3. Neighbors carry local information",
                "Most modes here use the eight surrounding Moore neighbors. The "
                "active mode guide states exactly what is counted.",
            ),
            TutorialSection(
                "4. One rule is copied everywhere",
                "No cell directs the board. Large structures emerge because the same "
                "small transition rule is applied repeatedly across the lattice.",
            ),
        ),
        kind="lattice",
    ),
    TutorialPage(
        "2D FOUNDATIONS 2 - TIME",
        "Everyone reads the same snapshot",
        (
            "For ordinary cellular automata, all cells read generation t and write "
            "generation t+1 together. This synchronous update prevents an early "
            "cell update from leaking into another cell's calculation."
        ),
        (
            TutorialSection(
                "1. Start from a seed",
                "The complete starting arrangement is generation 0. A small seed can "
                "be hand-drawn, randomized, or loaded from the pattern library.",
            ),
            TutorialSection(
                "2. Read before writing",
                "Each next state is calculated from the same old snapshot. Updating "
                "cells in place would define a different experiment.",
            ),
            TutorialSection(
                "3. One update is one generation",
                "Space runs continuously; N advances one generation while paused. "
                "The timeline records complete board snapshots through time.",
            ),
            TutorialSection(
                "4. Langton's Ant is the useful exception",
                "The ant changes one visited square and moves once per step. Its mode "
                "guide explains this agent-plus-lattice system separately.",
            ),
        ),
        kind="synchronous",
    ),
    TutorialPage(
        "2D FOUNDATIONS 3 - MODEL",
        "Four choices define the experiment",
        (
            "A screenshot alone does not identify a cellular-automaton experiment. "
            "Record the states, neighborhood, transition rule, and boundary or seed "
            "conditions before comparing two results."
        ),
        (
            TutorialSection(
                "1. State alphabet",
                "Conway uses two states; Brian's Brain uses three; Wireworld uses "
                "four; the Cyclic mode currently uses eight.",
            ),
            TutorialSection(
                "2. Neighborhood",
                "A Moore neighborhood has eight surrounding cells. Other models can "
                "use four faces, longer ranges, weighted cells, or moving agents.",
            ),
            TutorialSection(
                "3. Transition function",
                "The rule maps the current local configuration to the next state. "
                "Birth/survival counts are only one possible rule family.",
            ),
            TutorialSection(
                "4. Boundary and initial condition",
                "This app's 2D board is finite and does not wrap. Edge interactions, "
                "board size, seed, and duration can therefore change the result.",
            ),
        ),
        kind="model",
    ),
    TutorialPage(
        "2D FOUNDATIONS 4 - LAB WORKFLOW",
        "Observe, change one thing, measure",
        (
            "Treat each run as a reproducible experiment. Begin with a known seed, "
            "change one parameter, and use the timeline and analysis tools instead "
            "of judging a single attractive frame."
        ),
        (
            TutorialSection(
                "1. Prepare",
                "Pause, clear the board, then draw or load a mode-specific pattern. "
                "The active tool badge confirms what a left click will place.",
            ),
            TutorialSection(
                "2. Run and inspect",
                "Use Space to run, N to step, and the timeline to revisit a recorded "
                "generation without destroying the experiment.",
            ),
            TutorialSection(
                "3. Compare measurements",
                "Population, density, entropy, change rate and detected periods help "
                "separate stable, periodic, expanding, and chaotic behavior.",
            ),
            TutorialSection(
                "4. Save the evidence",
                "Store a session or profile, then export an image, animation, metrics "
                "CSV, or experiment JSON with its context intact.",
            ),
        ),
        kind="laboratory",
    ),
)


def _mode_pages(
    name: str,
    origin_lead: str,
    origin_sections: tuple[TutorialSection, ...],
    rule_lead: str,
    rule_sections: tuple[TutorialSection, ...],
    experiment_lead: str,
    experiment_sections: tuple[TutorialSection, ...],
) -> tuple[TutorialPage, ...]:
    return (
        TutorialPage(
            f"{name.upper()} 1 - IDENTITY",
            f"Meet {name}",
            origin_lead,
            origin_sections,
            kind="mode_identity",
        ),
        TutorialPage(
            f"{name.upper()} 2 - RULE",
            "Follow one update exactly",
            rule_lead,
            rule_sections,
            kind="mode_rule",
        ),
        TutorialPage(
            f"{name.upper()} 3 - EXPERIMENT",
            "What should you look for?",
            experiment_lead,
            experiment_sections,
            kind="mode_experiment",
        ),
        TutorialPage(
            f"{name.upper()} 4 - SOURCES",
            "Continue with reliable references",
            (
                "Only sources for the active mode appear here. Open a reference in "
                "your browser, then return to the same experiment without navigating "
                "through unrelated automata."
            ),
            kind="mode_sources",
        ),
    )


MODE_GUIDES: dict[str, ModeGuide] = {
    "life": ModeGuide(
        "Life-like",
        "Life-like",
        _mode_pages(
            "Life-like",
            (
                "John Conway devised the Game of Life in 1970; Martin Gardner's "
                "Scientific American column introduced it publicly that October. "
                "This workspace also includes related birth/survival rules."
            ),
            (
                TutorialSection("1. Creator", "John Horton Conway, 1970."),
                TutorialSection(
                    "2. Public introduction",
                    "Martin Gardner presented Life as a zero-player mathematical game.",
                ),
                TutorialSection(
                    "3. Model family",
                    "Two states, a square lattice, eight Moore neighbors, and an "
                    "outer-totalistic birth/survival rule.",
                ),
                TutorialSection(
                    "4. This app",
                    "The Rule button cycles Conway, HighLife, Day & Night, and Seeds.",
                ),
            ),
            (
                "A rulestring Bx/Sy lists the live-neighbor counts that create a dead "
                "cell (Birth) and preserve a live cell (Survival). Conway is B3/S23."
            ),
            (
                TutorialSection("1. Birth", "A dead Conway cell is born with exactly three live neighbors."),
                TutorialSection("2. Survival", "A live Conway cell survives with two or three live neighbors."),
                TutorialSection("3. Death", "Every other live cell dies from isolation or crowding."),
                TutorialSection("4. Simultaneity", "Every decision reads the same previous generation."),
            ),
            (
                "Life is best learned through named patterns. Stable forms, clocks, "
                "moving spaceships and long-lived methuselahs expose different kinds "
                "of global behavior produced by B3/S23."
            ),
            (
                TutorialSection("1. Still lifes", "Blocks and beehives remain unchanged."),
                TutorialSection("2. Oscillators", "Blinkers and pulsars repeat after a fixed period."),
                TutorialSection("3. Spaceships", "Gliders translate after several generations."),
                TutorialSection("4. Growth", "Guns, puffers and methuselahs reveal long transients or sustained production."),
            ),
        ),
        (
            TutorialSource("ORIGINAL INTRODUCTION", "Gardner (1970) - Mathematical Games", "The Scientific American column that introduced Conway's Life publicly.", SCIENTIFIC_AMERICAN_LIFE),
            TutorialSource("TEACHING MODEL", "NetLogo Models Library - Life", "A concise explanation of the board, rules, experiments and references.", NETLOGO_LIFE),
            TutorialSource("PATTERN ENCYCLOPEDIA", "LifeWiki - Conway's Game of Life", "Rules, history, terminology and links into the modern pattern catalogue.", LIFEWIKI_LIFE),
        ),
    ),
    "immigration": ModeGuide(
        "Immigration Game",
        "Immigration",
        _mode_pages(
            "Immigration Game",
            (
                "Don Woods created the Immigration Game in 1971 as a competitive, "
                "two-color extension of Conway's Life. Geometry still follows B3/S23; "
                "color records lineage and competition."
            ),
            (
                TutorialSection("1. Creator", "Don Woods, 1971."),
                TutorialSection("2. Shared geometry", "Ignoring color, the live/dead pattern evolves exactly as Conway Life."),
                TutorialSection("3. Two lineages", "Species A and B are symmetric live states, not stronger and weaker rules."),
                TutorialSection("4. Competition", "Only the parents of a new birth determine its inherited species."),
            ),
            (
                "Survival and birth use Conway's neighbor counts. A survivor keeps "
                "its species; a newborn takes the majority species among its three "
                "live parents."
            ),
            (
                TutorialSection("1. Count life first", "All A and B cells count equally toward B3/S23."),
                TutorialSection("2. Preserve survivors", "A surviving cell keeps its existing species."),
                TutorialSection("3. Color births", "A+A+B produces A; A+B+B produces B."),
                TutorialSection("4. No tie at birth", "Exactly three parents always give one species a two-to-one majority."),
            ),
            (
                "Use matched seeds to ask lineage questions: which species occupies "
                "more surviving cells, which collisions exchange territory, and "
                "whether geometry or ancestry determines the final census."
            ),
            (
                TutorialSection("1. Balance the start", "Place comparable A and B populations before interpreting a winner."),
                TutorialSection("2. Watch collisions", "Color can change only through births, not by converting survivors."),
                TutorialSection("3. Read the census", "The status bar reports both species counts and shares."),
                TutorialSection("4. Use accessible markers", "The Colorblind theme marks Species B by shape as well as color."),
            ),
        ),
        (
            TutorialSource("HISTORY & RESEARCH", "Conditions for Open-Ended Evolution in Immigration Games", "A modern paper that identifies Don Woods's 1971 game and studies competitive evolution.", IMMIGRATION_EVOLUTION),
            TutorialSource("RULE OVERVIEW", "LifeWiki - Variations on Life", "Explains Immigration as two ON states with majority-colored births.", LIFEWIKI_IMMIGRATION),
            TutorialSource("COLOR SYSTEM", "Multi-colored Life - Immigration", "Detailed notes on the two-color rule and its two-player origin.", MULTICOLORED_LIFE),
        ),
    ),
    "brians_brain": ModeGuide(
        "Brian's Brain",
        "Brian's Brain",
        _mode_pages(
            "Brian's Brain",
            (
                "Brian Silverman devised this well-known three-state Generations "
                "automaton. Its one-step refractory state makes moving waves and "
                "spaceships far more common than in Conway's Life."
            ),
            (
                TutorialSection("1. Creator", "Brian Silverman."),
                TutorialSection("2. Three phases", "Off, firing, and dying/refractory."),
                TutorialSection("3. Local geometry", "Eight Moore neighbors are inspected synchronously."),
                TutorialSection("4. Interpretation", "The neural language is a useful metaphor, not a biological brain model."),
            ),
            (
                "Only firing neighbors count. An off cell fires with exactly two "
                "firing neighbors; every firing cell becomes dying, and every dying "
                "cell becomes off."
            ),
            (
                TutorialSection("1. Excitation", "OFF + exactly two FIRING neighbors becomes FIRING."),
                TutorialSection("2. Refractory step", "Every FIRING cell becomes DYING after one generation."),
                TutorialSection("3. Recovery", "Every DYING cell becomes OFF after one generation."),
                TutorialSection("4. Neighbor count", "DYING cells do not count as firing neighbors."),
            ),
            (
                "The refractory trail gives patterns direction. Start with verified "
                "seeds and look for diagonal waves, spaceships, rakes, expanding "
                "fronts and the rarer stable-period oscillators."
            ),
            (
                TutorialSection("1. Follow the wavefront", "Firing cells lead; dying cells form the temporary wake."),
                TutorialSection("2. Distinguish motion", "Many small seeds translate rather than merely blink."),
                TutorialSection("3. Avoid overfilling", "Dense random starts can become visually noisy very quickly."),
                TutorialSection("4. Step through phases", "Use N and the timeline to separate firing from refractory motion."),
            ),
        ),
        (
            TutorialSource("TEACHING MODEL", "NetLogo Models Library - Brian's Brain", "Rules, experiments and credits from Northwestern's educational model library.", NETLOGO_BRAINS_BRAIN),
            TutorialSource("RULE ENCYCLOPEDIA", "LifeWiki - Brian's Brain", "Generations notation, history, behavior and known patterns.", LIFEWIKI_BRAINS_BRAIN),
        ),
    ),
    "langtons_ant": ModeGuide(
        "Langton's Ant",
        "Langton's Ant",
        _mode_pages(
            "Langton's Ant",
            (
                "Christopher Langton introduced the virtual ant in 1986 while studying "
                "artificial life. It combines a two-color lattice with one directional "
                "agent, so one square changes per step."
            ),
            (
                TutorialSection("1. Creator", "Christopher G. Langton, 1986."),
                TutorialSection("2. Board memory", "Each square stores white or black."),
                TutorialSection("3. Agent memory", "The ant stores position and one of four headings."),
                TutorialSection("4. Important exception", "This is sequential agent motion, not a simultaneous whole-grid update."),
            ),
            (
                "Read the color under the ant, turn, flip that square, then move one "
                "step forward. Changing this operation order defines a different system."
            ),
            (
                TutorialSection("1. On white", "Turn 90 degrees right and paint the square black."),
                TutorialSection("2. On black", "Turn 90 degrees left and paint the square white."),
                TutorialSection("3. Then move", "Advance exactly one cell in the new heading."),
                TutorialSection("4. At this board edge", "The finite non-wrapping simulation stops when the ant exits."),
            ),
            (
                "A blank board passes through a long irregular phase before the famous "
                "periodic highway often appears. Initial black cells and ant direction "
                "can radically change the transient route."
            ),
            (
                TutorialSection("1. Place the agent", "Shift + left click moves the ant; T rotates it in place."),
                TutorialSection("2. Read its shape", "The triangle shows heading without relying only on color."),
                TutorialSection("3. Compare transients", "Use different finite seeds and measure when order appears."),
                TutorialSection("4. Protect the run", "Center the ant or enlarge the visible board before a long experiment."),
            ),
        ),
        (
            TutorialSource("ORIGINAL PAPER", "Langton (1986) - Studying Artificial Life with Cellular Automata", "The Physica D paper that introduced the virtual ant in its artificial-life context.", LANGTON_ORIGINAL),
            TutorialSource("COMPUTATIONAL RESULT", "Gajardo et al. - Complexity of Langton's Ant", "A proof-oriented study connecting the ant to circuit and universal computation.", LANGTON_COMPLEXITY),
        ),
    ),
    "wireworld": ModeGuide(
        "Wireworld",
        "Wireworld",
        _mode_pages(
            "Wireworld",
            (
                "Brian Silverman proposed Wireworld in 1987; A. K. Dewdney's 1990 "
                "Scientific American column helped popularize it. Static conductor "
                "geometry guides moving electron signals."
            ),
            (
                TutorialSection("1. Creator", "Brian Silverman, 1987."),
                TutorialSection("2. Four states", "Empty, conductor, electron head, and electron tail."),
                TutorialSection("3. Circuit viewpoint", "Conductor shapes encode wires and logic; head/tail pairs encode moving signals."),
                TutorialSection("4. Synchronous CA", "Every wire cell advances from the same previous generation."),
            ),
            (
                "Heads become tails, tails become conductors, and a conductor becomes "
                "a new head only when exactly one or two neighboring cells are heads."
            ),
            (
                TutorialSection("1. Empty", "EMPTY remains EMPTY."),
                TutorialSection("2. Signal motion", "HEAD becomes TAIL; TAIL becomes CONDUCTOR."),
                TutorialSection("3. Signal reception", "A CONDUCTOR with one or two neighboring HEADS becomes HEAD."),
                TutorialSection("4. Otherwise", "A conductor with zero or at least three heads stays CONDUCTOR."),
            ),
            (
                "Wireworld is most meaningful as a circuit laboratory. Begin with a "
                "verified clock or signal, then inspect diodes, gates, memory, and the "
                "binary adder one generation at a time."
            ),
            (
                TutorialSection("1. Build geometry first", "Draw or load the complete conductor path before adding a signal."),
                TutorialSection("2. Give direction", "Place a head with a tail behind it to form a moving pulse."),
                TutorialSection("3. Inspect timing", "Logic depends on signals reaching a junction at the intended generation."),
                TutorialSection("4. Use the catalogue", "The mode library includes gates, diode, flip-flop and binary-adder examples."),
            ),
        ),
        (
            TutorialSource("HISTORICAL ARTICLE", "Dewdney (1990) - Computer Recreations", "The Scientific American article that popularized Wireworld and related automata.", SCIENTIFIC_AMERICAN_WIREWORLD),
            TutorialSource("CIRCUIT TUTORIAL", "Quinapalus - Wireworld", "A visual progression from signals through diodes and Boolean logic circuits.", QUINAPALUS_WIREWORLD),
        ),
    ),
    "cyclic_automaton": ModeGuide(
        "Cyclic Cellular Automaton",
        "Cyclic CA",
        _mode_pages(
            "Cyclic Cellular Automaton",
            (
                "Robert Fisch formalized cyclic cellular automata in work published "
                "in 1990. Colors compete in a directed cycle: each state can be "
                "replaced only by its immediate successor."
            ),
            (
                TutorialSection("1. Early framework", "Robert Fisch's 1990 cyclic cellular-automata study."),
                TutorialSection("2. State cycle", "This app uses eight states arranged 0 -> 1 -> ... -> 7 -> 0."),
                TutorialSection("3. Local geometry", "Each cell inspects eight Moore neighbors."),
                TutorialSection("4. Threshold variant", "A selectable contact threshold controls how much successor pressure is required."),
            ),
            (
                "A cell in state s counts neighbors in state (s+1) mod 8. It advances "
                "only when that count reaches the selected threshold; otherwise it "
                "keeps state s."
            ),
            (
                TutorialSection("1. Find the successor", "For state 7 the successor wraps back to state 0."),
                TutorialSection("2. Count only that color", "Other neighboring states do not contribute to the threshold."),
                TutorialSection("3. Compare to threshold", "At or above the threshold, advance exactly one state."),
                TutorialSection("4. Update together", "All color changes read the same previous generation."),
            ),
            (
                "A randomized state field reveals traveling fronts and spiral cores. "
                "Low thresholds spread quickly; high thresholds resist change and can "
                "lock large regions."
            ),
            (
                TutorialSection("1. Randomize", "Uniformly seed all eight states to expose cyclic competition."),
                TutorialSection("2. Sweep the threshold", "Change only the threshold and compare equal-duration runs."),
                TutorialSection("3. Track organization", "Watch entropy, change rate, state diversity and dominant share."),
                TutorialSection("4. Inspect fronts", "Use stepping and the timeline to follow one color boundary through the cycle."),
            ),
        ),
        (
            TutorialSource("FOUNDATIONAL PAPER", "Fisch (1990) - Cyclic Cellular Automata and Related Processes", "Defines the deterministic cyclic process and relates it to cyclic particle systems.", FISCH_CYCLIC),
            TutorialSource("THRESHOLD STUDY", "Fisch, Gravner & Griffeath - Threshold-Range Scaling", "Research on contact thresholds and excitable cellular-automaton phase behavior.", CYCLIC_THRESHOLD),
        ),
    ),
}


def validate_curriculum() -> None:
    """Raise a clear error if the static curriculum is internally inconsistent."""
    if len(FOUNDATION_PAGES) != 4:
        raise ValueError("The 2D foundation curriculum must contain four pages.")
    for mode, guide in MODE_GUIDES.items():
        if len(guide.pages) != 4:
            raise ValueError(f"The {mode} guide must contain four pages.")
        if not guide.sources:
            raise ValueError(f"The {mode} guide must contain at least one source.")
        if any(not source.url.startswith("https://") for source in guide.sources):
            raise ValueError(f"The {mode} guide contains an unsafe source URL.")


validate_curriculum()
