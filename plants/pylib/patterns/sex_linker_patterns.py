"""Link traits to a plant's sex.

We want to handle sexual dimorphism by linking traits to a plant's sex.
For example: "petals (1–)3–10(–12) mm (pistillate) or 5–8(–10) mm (staminate):
Should note that pistillate petals are 3-10 mm and staminate petals are 5-8 mm.
Named entity recognition (NER) must be run first.
"""
from traiter.pylib.pattern_compilers.matcher_compiler import MatcherCompiler
from traiter.pylib.patterns import common_patterns

from . import term_patterns


SEX_PARENTS = ["sex"]
SEX_CHILDREN = term_patterns.all_traits_except(["sex"] + term_patterns.NO_LINK)

SEX_LINKER = MatcherCompiler(
    "sex_linker",
    decoder=common_patterns.COMMON_PATTERNS
    | {
        "sex": {"ENT_TYPE": {"IN": SEX_PARENTS}},
        "trait": {"ENT_TYPE": {"IN": SEX_CHILDREN}},
    },
    patterns=[
        "trait phrase* sex",
        "sex   phrase* trait",
    ],
)
