"""Curriculum and references for the contextual three-dimensional tutorial."""

from __future__ import annotations

from three_dimensional_modes import MODE_GENERATIONS, MODE_SPATIAL_LIFE
from two_dimensional_tutorial_content import (
    ModeGuide,
    TutorialPage,
    TutorialSection,
    TutorialSource,
)


BAYS_GLIDER_PAPER = (
    "https://www.complex-systems.com/abstracts/v04_i06_a02/"
)
BAYS_GLIDER_CATALOG = "https://www.ibiblio.org/e-notes/Life/Gliders.htm"
SOFTOLOGY_3D_CA = (
    "https://softologyblog.wordpress.com/2019/12/28/3d-cellular-automata-3/"
)
SOFTOLOGY_VISIONS_OF_CHAOS = "https://softology.pro/voc.htm"
PARAMETRIC_HOUSE_3D_CA = "https://parametrichouse.com/3d-cellular-automata/"
WILLIAM_YANG_3D_CA = "https://github.com/williamyang98/3D-Cellular-Automata"


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


THREE_D_FOUNDATION_PAGES: tuple[TutorialPage, ...] = (
    _page(
        "3D FOUNDATIONS 1 - VOLUME",
        "The world is a volume, not three stacked pictures",
        "Every position has an x, y, and z coordinate and stores one voxel state. The default orthographic view projects that cubic lattice without converging parallel edges; it does not turn depth into time.",
        "volume",
        _section("A true 3D lattice", "Rows, columns, and depth are all spatial directions. A voxel can have neighbors in front of and behind the screen plane."),
        _section("One state per coordinate", "The volume is a NumPy uint8 array addressed internally as (z, y, x). The camera changes only how those coordinates are viewed."),
        _section("Visible cubes are occupied states", "Empty state-0 positions are normally invisible. The wireframe box shows the complete finite experiment volume."),
        _section("Projection is not simulation", "Orbiting, zooming, clipping, and recoloring do not change any voxel state or generation."),
    ),
    _page(
        "3D FOUNDATIONS 2 - NEIGHBORHOODS",
        "Six face neighbors and twenty-six Moore neighbors",
        "A 3×3×3 block contains 27 positions. Remove the focus voxel: all remaining 26 form the 3D Moore neighborhood; only the six face-sharing positions form the 3D von Neumann neighborhood.",
        "neighborhoods",
        _section("Six-face neighborhood", "The ±X, ±Y, and ±Z voxels share a complete face with the focus voxel."),
        _section("Twenty-six-cell Moore neighborhood", "Six face, twelve edge, and eight corner contacts all count equally."),
        _section("Never count the focus voxel", "The center's current state selects a rule branch, but it is not included in its own neighbor total."),
        _section("Rule compatibility", "Bays rules and all current Generations presets use 26 neighbors. Face Life deliberately uses only six."),
    ),
    _page(
        "3D FOUNDATIONS 3 - TIME",
        "Freeze the old volume, calculate, then commit",
        "Like ordinary 2D cellular automata, every voxel reads generation t and writes into a separate generation t+1 volume. The complete new volume replaces the old one only after all local decisions are ready.",
        "synchronous_3d",
        _section("Read one snapshot", "A voxel cannot see a neighbor that was born earlier in the same generation."),
        _section("Calculate independently", "Neighbor counts are computed from the immutable old volume for every coordinate."),
        _section("Commit together", "Births, survivals, deaths, and refractory advances become visible simultaneously."),
        _section("Repeat discrete generations", "Space runs in x, y, and z; generation is a separate time coordinate recorded by the timeline."),
    ),
    _page(
        "3D FOUNDATIONS 4 - VISIBILITY",
        "The surface can hide most of the experiment",
        "A dense voxel structure may contain active cavities and internal fronts that an exterior view cannot reveal. Use opacity, clipping, and single-layer inspection as scientific instruments, not merely visual effects.",
        "visibility",
        _section("Orbit", "Rotate around the same data to separate depth overlap from real contact."),
        _section("Opacity", "Lower opacity reveals internal voxels while preserving full-volume context."),
        _section("Clipping plane", "Keep only one side of an X, Y, or Z plane and move the plane through the structure."),
        _section("Single layer", "Isolate one lattice layer to inspect exact cell states without occlusion."),
    ),
    _page(
        "3D FOUNDATIONS 5 - CAMERA",
        "Move the viewpoint without moving the automaton",
        "The camera orbits a target inside the volume. Pan changes that target, zoom changes distance, and the orientation cube snaps a selected face toward the screen.",
        "camera_3d",
        _section("Left drag", "Orbit around the camera target; no voxels move in world coordinates."),
        _section("Middle drag", "Pan the target parallel to the view plane."),
        _section("Mouse wheel", "Change camera distance to zoom."),
        _section("Orientation cube", "Click a visible cube face for an aligned ±X, ±Y, or ±Z view; Ctrl+0 fits the full volume."),
        _section("Projection", "Orthographic is the shape-accurate scientific default. Use Camera & View to enable perspective when depth convergence is useful."),
    ),
    _page(
        "3D FOUNDATIONS 6 - EDITING",
        "A screen click becomes a ray through the volume",
        "The editor casts a ray from the camera through the pointer. It selects the first occupied voxel hit and the face crossed, which makes addition and erasure unambiguous in depth.",
        "editing_3d",
        _section("Left click", "Add the active voxel state in the empty cell immediately outside the hit face."),
        _section("Right click", "Erase the first occupied voxel hit by the ray."),
        _section("Rotate before editing", "An aligned face view and clipping plane make deep edits easier to predict."),
        _section("State brush", "In multi-state rules the active brush chooses which voxel state a left click places."),
    ),
    _page(
        "3D FOUNDATIONS 7 - EXPERIMENT",
        "Control scale, boundaries, seed, and observation",
        "Three-dimensional experiments grow expensive quickly: 32³ is 32,768 cells, 48³ is 110,592, and 64³ is 262,144. Change one variable at a time and save enough context to reproduce the run.",
        "laboratory_3d",
        _section("Choose a finite volume", "Use 32³ while learning, 48³ for routine experiments, and 64³ only when the structure needs room."),
        _section("Record the boundary", "Fixed, wrapped, and reflected boundaries can make identical seeds diverge after reaching an edge."),
        _section("Inspect through time", "Use N, the timeline, clipping, and analysis metrics instead of judging one exterior frame."),
        _section("Save evidence", "Sessions preserve rule, volume, boundary, camera, view filters, generation, and timeline context."),
    ),
)


SPATIAL_LIFE_PAGES: tuple[TutorialPage, ...] = (
    _page(
        "SPATIAL LIFE 1 - IDENTITY",
        "Carter Bays' cubic Life candidates",
        "Carter Bays studied binary three-dimensional Life rules, including Life 4555 and Life 5766. These are not Conway's B3/S23 copied unchanged into another dimension: 26 possible neighbors require different birth and survival counts.",
        "mode_identity_3d",
        _section("Research line", "Bays published candidates and gliders for cubic three-dimensional Life in Complex Systems."),
        _section("Two states", "Every voxel is empty or alive."),
        _section("Synchronous volume", "All binary voxels update together from local 3D neighbor counts."),
        _section("Default here", "Bays 5766 uses six-neighbor birth and survival with five, six, or seven live neighbors."),
    ),
    _page(
        "SPATIAL LIFE 2 - NOTATION",
        "Read B6/S567 in three dimensions",
        "The app writes birth first and survival second. B6/S567 is the same rule historically called Life 5766: an empty voxel is born with 6 neighbors; a live voxel survives with 5, 6, or 7.",
        "spatial_notation",
        _section("B = birth", "Apply the B list only when the focus voxel is currently empty."),
        _section("S = survival", "Apply the S list only when the focus voxel is currently alive."),
        _section("Count active voxels", "For Bays rules, count all 26 surrounding Moore positions and only state 1."),
        _section("Current preset", "The tutorial header follows the selected Spatial Life rule, while examples label which preset they demonstrate."),
    ),
    _page(
        "SPATIAL LIFE 3 - BIRTH",
        "Why an empty voxel is born in Bays 5766",
        "The transparent focus voxel has exactly six live Moore neighbors in generation t. Six matches B6, so the focus becomes alive when generation t+1 is committed.",
        "spatial_birth",
        _section("Read", "The focus voxel is empty, so the survival list is irrelevant."),
        _section("Count", "Exactly six of the possible 26 neighboring positions are alive."),
        _section("Match B6", "Six appears in the birth list."),
        _section("Write", "The next volume receives one live voxel at the focus coordinate."),
    ),
    _page(
        "SPATIAL LIFE 4 - SURVIVAL AND DEATH",
        "Why a live voxel survives or disappears",
        "Under Bays 5766, a live focus survives with 5, 6, or 7 live neighbors. Counts below five or above seven write an empty voxel into the next volume.",
        "spatial_survival",
        _section("Five", "The focus survives."),
        _section("Six", "The focus survives."),
        _section("Seven", "The focus survives."),
        _section("Every other count", "The focus dies; no refractory trail is stored in binary Spatial Life."),
    ),
    _page(
        "SPATIAL LIFE 5 - GLIDER",
        "A ten-voxel pattern translates after four generations",
        "The documented Bays 5766 glider has period four. After four synchronous updates its shape repeats one cell away along a diagonal direction.",
        "spatial_glider",
        _section("Load the verified seed", "The Bays 5766 Glider button installs its ten coordinates and compatible rule."),
        _section("Step four times", "Use N and compare generations 0 and 4 from several camera angles."),
        _section("Distinguish period from position", "The shape repeats, but its coordinates are translated."),
        _section("Boundary", "The documented preset uses wrapping so continued motion can cross a volume edge."),
    ),
    _page(
        "SPATIAL LIFE 6 - OTHER PRESETS",
        "Neighborhood and count lists define different experiments",
        "Bays 4555 keeps the 26-neighbor geometry but changes counts. Face Life uses familiar B3/S23 counts only after replacing the Moore shell with six face neighbors.",
        "spatial_catalog",
        _section("Bays 4555", "B5/S45 on 26 Moore neighbors: birth with five, survival with four or five."),
        _section("Face Life", "B3/S23 on only six face-sharing neighbors; an exploratory comparison, not Conway's 2D lattice."),
        _section("Do not compare notation alone", "B3/S23 with six neighbors is a different rule from B3/S23 with eight 2D neighbors."),
        _section("Reset after a rule change", "A documented seed should be evaluated under the rule and boundary it was designed for."),
    ),
    _page(
        "SPATIAL LIFE 7 - PLAY AND MEASURE",
        "Test bounded growth, motion, and sensitivity",
        "Begin with a verified glider or a small centered seed. Dense random starts can hide local structures and reach finite boundaries quickly.",
        "mode_experiment_3d",
        _section("Start small", "Use 32³ and a sparse centered seed while learning the rule."),
        _section("Inspect the interior", "Compare full volume, clipping, and single-layer views at the same generation."),
        _section("Track population", "Growth, extinction, oscillation, and translation require timeline evidence."),
        _section("Compare fairly", "Keep seed, volume, and boundary fixed while changing one rule."),
    ),
    _page("SPATIAL LIFE 8 - SOURCES", "Continue with reliable references", "Only references relevant to Spatial Life and its documented glider appear here.", "mode_sources"),
)


GENERATIONS_PAGES: tuple[TutorialPage, ...] = (
    _page(
        "3D GENERATIONS 1 - IDENTITY",
        "Active voxels can leave refractory history",
        "Generations rules extend Life-like birth and survival with more than two states. State 1 is active; optional states 2 and above form a deterministic cooling trail before the voxel becomes empty again.",
        "mode_identity_3d",
        _section("Rule family", "A multi-state generalization of birth/survival cellular automata."),
        _section("Three-dimensional form", "The current presets count active voxels in a cubic Moore neighborhood."),
        _section("Documented presets", "445, 3D Brain, Clouds 1, and Pyroclastic follow the rule list documented by Softology."),
        _section("Corrected logic", "Only active state 1 can survive or count as a neighbor; refractory states only cool toward zero."),
    ),
    _page(
        "3D GENERATIONS 2 - STATE CYCLE",
        "State 1 is active; higher states are a one-way cooldown",
        "An empty voxel can be born into state 1. If active state 1 fails survival, it enters state 2. Refractory states then advance 2→3→…→C−1→0 without being reactivated midway.",
        "generations_states",
        _section("State 0", "Empty and eligible for birth when the B count matches."),
        _section("State 1", "The only active state; the only state counted by neighbors and eligible for survival."),
        _section("States 2 through C−1", "Refractory history. They do not count, survive, or receive a new birth."),
        _section("Return to 0", "After the final refractory state, the coordinate becomes empty and can be born again later."),
    ),
    _page(
        "3D GENERATIONS 3 - NOTATION",
        "Read survival / birth / states / neighborhood",
        "The preset 4/4/5/M means survival with four active neighbors, birth with four, five total states, and a 26-cell Moore neighborhood.",
        "generations_notation",
        _section("First field - survival", "Counts that keep a state-1 voxel active."),
        _section("Second field - birth", "Counts that create state 1 in an empty state-0 coordinate."),
        _section("Third field - C", "Total states including 0 and 1; values above two create refractory history."),
        _section("Fourth field", "M means 26-cell Moore; N would mean the six face-sharing von Neumann neighbors."),
    ),
    _page(
        "3D GENERATIONS 4 - WHAT COUNTS",
        "Count only state-1 neighbors",
        "A focus voxel may be surrounded by bright active voxels and visible refractory voxels. Only state 1 contributes to survival and birth counts; color or visibility does not imply activity.",
        "generations_counting",
        _section("Active evidence", "Every neighboring state-1 voxel contributes one."),
        _section("Refractory evidence", "States 2 and above contribute zero even though they remain rendered."),
        _section("Focus branch", "State 0 checks birth; state 1 checks survival; refractory states simply advance."),
        _section("Use state shading", "The State Shading color scheme is the clearest way to distinguish active fronts from old trails."),
    ),
    _page(
        "3D GENERATIONS 5 - RULE 445",
        "Follow 4/4/5/M without skipping a state",
        "Rule 445 has states 0, 1, 2, 3, and 4. Empty plus four active neighbors is born; active plus four survives; every other active voxel begins the fixed cooldown 2→3→4→0.",
        "generations_445",
        _section("Birth", "State 0 with exactly four state-1 neighbors becomes state 1."),
        _section("Survival", "State 1 with exactly four state-1 neighbors remains state 1."),
        _section("Failed survival", "State 1 with another count becomes state 2."),
        _section("Cooldown", "2 becomes 3, 3 becomes 4, and 4 becomes 0 regardless of neighbors."),
    ),
    _page(
        "3D GENERATIONS 6 - BINARY PRESETS",
        "Two states remove the refractory trail",
        "3D Brain and Clouds 1 use C=2. A failed active cell therefore goes directly to empty, just like a binary rule, although their count lists differ greatly.",
        "generations_binary",
        _section("3D Brain /4/2/M", "No survival count; an empty voxel is born with four active neighbors, while every old active voxel dies."),
        _section("Clouds 1", "Survival 13–26; birth 13–14 or 17–19; two states; dense random seed."),
        _section("Same engine", "Both still use state 1 as the only counted active state."),
        _section("Different density regime", "A rule requiring thirteen neighbors needs a much denser initial core than one requiring four."),
    ),
    _page(
        "3D GENERATIONS 7 - PYROCLASTIC",
        "Ten states turn death into a long visible trail",
        "Pyroclastic 4–7/6–8/10/M keeps active voxels with four through seven neighbors, births with six through eight, and stores eight refractory steps after failed survival.",
        "generations_pyroclastic",
        _section("Active front", "State 1 participates in birth and survival decisions."),
        _section("Long wake", "States 2 through 9 record progressively older deaths."),
        _section("No resurrection", "A refractory voxel cannot become active before reaching state 0."),
        _section("Visual reading", "State shading and clipping reveal the moving front separately from its accumulated trail."),
    ),
    _page(
        "3D GENERATIONS 8 - PLAY AND MEASURE",
        "Match seed density to the selected rule",
        "The Random Central Core command uses each preset's documented density. Compare presets from fresh cores instead of carrying a mature volume into an unrelated rule.",
        "mode_experiment_3d",
        _section("Reset on rule change", "Generate a fresh central core after selecting 445, 3D Brain, Clouds 1, or Pyroclastic."),
        _section("Watch active and refractory states", "Total occupied voxels alone can rise while current activity is falling."),
        _section("Inspect slices", "Move a clipping plane through dense clouds and trails."),
        _section("Compare equal durations", "Keep volume, boundary, seed method, and generation count fixed."),
    ),
    _page("3D GENERATIONS 9 - SOURCES", "Continue with reliable references", "Only references relevant to the active 3D Generations family appear here.", "mode_sources"),
)


THREE_D_MODE_GUIDES: dict[str, ModeGuide] = {
    MODE_SPATIAL_LIFE: ModeGuide(
        "Spatial Life",
        "Spatial Life",
        SPATIAL_LIFE_PAGES,
        (
            TutorialSource("PRIMARY PAPER", "Bays (1990) - A New Glider for Three-Dimensional Life", "The Complex Systems paper describing Life 4555, Life 5766, and a documented glider.", BAYS_GLIDER_PAPER),
            TutorialSource("GLIDER CATALOG", "3D Gliders - Bays 5766", "Coordinates and animations for known three-dimensional gliders.", BAYS_GLIDER_CATALOG),
            TutorialSource("VISUALIZATION & NEIGHBORHOODS", "Softology - 3D Cellular Automata", "Clear explanations of 26-cell Moore and six-cell face neighborhoods plus rendering methods.", SOFTOLOGY_3D_CA),
        ),
    ),
    MODE_GENERATIONS: ModeGuide(
        "3D Generations",
        "3D Generations",
        GENERATIONS_PAGES,
        (
            TutorialSource("RULE REFERENCE", "Softology - 3D Cellular Automata", "The rule notation, 445 walkthrough, corrected state logic, preset list, and coloring methods used by this mode.", SOFTOLOGY_3D_CA),
            TutorialSource("REFERENCE SOFTWARE", "Visions of Chaos", "The application in which the documented 3D Generations presets can be reproduced and compared.", SOFTOLOGY_VISIONS_OF_CHAOS),
            TutorialSource("VISUAL EXAMPLE", "Parametric House - 3D Cellular Automata", "An accessible visual introduction to voxel-based three-dimensional cellular automata.", PARAMETRIC_HOUSE_3D_CA),
            TutorialSource("OPEN-SOURCE EXAMPLE", "William Yang - 3D Cellular Automata", "A Softology-inspired implementation useful for comparing rendering and experiment structure.", WILLIAM_YANG_3D_CA),
        ),
    ),
}


def validate_curriculum() -> None:
    """Validate mode coverage, lesson depth, and safe external references."""
    if len(THREE_D_FOUNDATION_PAGES) != 7:
        raise ValueError("The 3D foundation curriculum must contain seven lessons.")
    if set(THREE_D_MODE_GUIDES) != {MODE_SPATIAL_LIFE, MODE_GENERATIONS}:
        raise ValueError("The 3D tutorial must cover every registered mode.")
    for mode, guide in THREE_D_MODE_GUIDES.items():
        if len(guide.pages) < 8:
            raise ValueError(f"The {mode} guide is unexpectedly short.")
        if guide.pages[-1].kind != "mode_sources":
            raise ValueError(f"The {mode} guide must finish with references.")
        if not guide.sources:
            raise ValueError(f"The {mode} guide requires at least one reference.")
        if any(not source.url.startswith("https://") for source in guide.sources):
            raise ValueError(f"The {mode} guide contains an unsafe source URL.")


validate_curriculum()
