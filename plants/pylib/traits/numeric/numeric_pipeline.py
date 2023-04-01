from pathlib import Path

from spacy import Language
from traiter.pylib.traits import add_pipe as add
from traiter.pylib.traits import month
from traiter.pylib.traits import numeric as t_numeric
from traiter.pylib.traits import trait_util
from traiter.pylib.traits import units

from .custom_pipe_count import CUSTOM_PIPE_COUNT
from .custom_pipe_range import CUSTOM_PIPE_RANGE
from .custom_pipe_size import CUSTOM_PIPE_SIZE
from .pattern_compilers_count import COMPILERS as COUNT_COMPILERS
from .pattern_compilers_range import COMPILERS as RANGE_COMPILERS
from .pattern_compilers_size import COMPILERS as SIZE_COMPILERS
from .pattern_compilers_size import LENGTH_ENTS

HERE = Path(__file__).parent
TRAIT = HERE.stem

CSV = HERE / f"{TRAIT}.csv"
MONTH_CSV = Path(month.__file__).parent / "month.csv"
NUMERIC_CSV = Path(t_numeric.__file__).parent / "numeric.csv"
SEX_CSV = HERE.parent / "basic" / "sex.csv"
UNITS_CSV = Path(units.__file__).parent / "units_length.csv"
ALL_CSV = [CSV, MONTH_CSV, NUMERIC_CSV, SEX_CSV, UNITS_CSV]


def build(nlp: Language, **kwargs):
    with nlp.select_pipes(enable="tokenizer"):
        prev = add.term_pipe(nlp, name=f"{TRAIT}_terms", path=ALL_CSV, **kwargs)

    prev = add.ruler_pipe(
        nlp,
        name="range_patterns",
        compiler=RANGE_COMPILERS,
        overwrite_ents=False,
        after=prev,
    )

    config = {"trait": "range"}
    prev = add.custom_pipe(nlp, CUSTOM_PIPE_RANGE, config=config, after=prev)

    prev = add.ruler_pipe(
        nlp,
        name="numeric_patterns",
        compiler=COUNT_COMPILERS + SIZE_COMPILERS,
        overwrite_ents=True,
        after=prev,
    )

    # from traiter.pylib.pipes import debug  # #####################################
    # prev = debug.tokens(nlp, after=prev)  # ######################################

    replace = trait_util.term_data(CSV, "replace")
    replace |= trait_util.term_data(NUMERIC_CSV, "replace")

    config = {
        "trait": "count",
        "replace": replace,
    }
    prev = add.custom_pipe(nlp, CUSTOM_PIPE_COUNT, config=config, after=prev)

    config = {
        "trait": "size",
        "replace": replace,
        "units_replace": trait_util.term_data(UNITS_CSV, "replace"),
        "units_labels": LENGTH_ENTS,
        "factors_cm": trait_util.term_data(UNITS_CSV, "factor_cm", float),
    }
    prev = add.custom_pipe(nlp, CUSTOM_PIPE_SIZE, config=config, after=prev)

    remove = trait_util.labels_to_remove(ALL_CSV, keep=["count", "size"])
    remove += ["not_a_count"]
    prev = add.cleanup_pipe(nlp, name=f"{TRAIT}_cleanup", remove=remove, after=prev)

    return prev
