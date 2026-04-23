"""One-level reference expansion for artifact detail responses."""
from __future__ import annotations

from typing import Any, Dict

from . import models


def _bilingual(b: models.BilingualString | None) -> Dict[str, str] | None:
    return b.model_dump() if b else None


def expand_artifact(artifact: models.Artifact, ontology) -> Dict[str, Any]:
    """Return the artifact serialized with hall / dynasty / persons
    objects substituted in place of bare ID fields.

    Does NOT recurse further: nested objects appear as summaries only.
    """
    hall = ontology.halls[artifact.hallId]
    dyn  = ontology.dynasties[artifact.dynastyId]
    persons_full = [ontology.persons[pid] for pid in artifact.personIds]

    data = artifact.model_dump()
    data.pop("hallId", None)
    data.pop("dynastyId", None)
    data.pop("personIds", None)

    data["hall"] = {
        "id":   hall.id,
        "name": hall.name.model_dump(),
        "floor": hall.floor,
        "theme": _bilingual(hall.theme),
    }
    data["dynasty"] = {
        "id": dyn.id,
        "name":   dyn.name.model_dump(),
        "period": dyn.period.model_dump(),
        "predecessor": dyn.predecessor,
        "successor":   dyn.successor,
        "shortDesc":   _bilingual(dyn.shortDesc),
    }
    data["persons"] = [
        {
            "id":   p.id,
            "name": p.name.model_dump(),
            "role": p.role.model_dump(),
            "dynastyId": p.dynastyId,
            "shortDesc": _bilingual(p.shortDesc),
        }
        for p in persons_full
    ]
    return data
