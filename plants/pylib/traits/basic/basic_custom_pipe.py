from dataclasses import dataclass

from spacy import Language
from traiter.pylib.traits.base_custom_pipe import BaseCustomPipe

BASIC_CUSTOM_PIPE = "basic_custom_pipe"


@Language.factory(BASIC_CUSTOM_PIPE)
@dataclass()
class BasicPipe(BaseCustomPipe):
    replace: dict[str, str]
    labels: list[str]

    def __call__(self, doc):
        for ent in [e for e in doc.ents if e.label_ in self.labels]:
            frags = []
            for token in ent:
                if token.text not in "[ ] ( )":
                    frags.append(self.replace.get(token.lower_, token.lower_))
            ent._.data[ent.label_] = " ".join(frags)
        return doc