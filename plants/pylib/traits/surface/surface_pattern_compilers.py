from traiter.pylib import const as t_const
from traiter.pylib.traits.pattern_compiler import Compiler


def surface_compilers():
    return [
        Compiler(
            label="surface",
            decoder={
                "-": {"TEXT": {"IN": t_const.DASH}},
                "surface": {"ENT_TYPE": "surface_term"},
                "surface_leader": {"ENT_TYPE": "surface_leader"},
            },
            patterns=[
                "                  surface",
                "surface_leader -? surface",
            ],
        ),
    ]
