from traiter.pylib.pattern_compilers.matcher_compiler import MatcherCompiler
from traiter.pylib.patterns import common_patterns

TAXON_LIKE_PARENTS = ["taxon_like"]
TAXON_LIKE_CHILDREN = ["taxon"]

TAXON_LIKE_LINKER = MatcherCompiler(
    "taxon_like_linker",
    decoder=common_patterns.COMMON_PATTERNS
    | {
        "taxon_like": {"ENT_TYPE": {"IN": TAXON_LIKE_PARENTS}},
        "taxon": {"ENT_TYPE": {"IN": TAXON_LIKE_CHILDREN}},
    },
    patterns=[
        "taxon      any* taxon_like",
        "taxon_like any* taxon",
    ],
)
