"""Load the persona conversations from personas/*.yaml."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from .checks import facts

PERSONA_DIR = Path(__file__).resolve().parent.parent / "personas"
_FILLER = "lorem ipsum dolor sit amet consectetur adipiscing elit "


@dataclass
class Turn:
    id: str
    user: str
    expect: list[dict] = field(default_factory=list)
    reference: str = ""            # an example of a reply that should pass
    tags: list[str] = field(default_factory=list)
    allow_status: list[int] = field(default_factory=lambda: [200])
    abuse: bool = False            # only sent with --run-abuse
    burst: int = 0                 # send this many copies back to back
    cooldown_s: float = 0.0        # pause after the turn


@dataclass
class Persona:
    id: str
    name: str
    label: str
    kind: str                      # "typical" or "edge"
    who: str
    question_types: list[int]
    turns: list[Turn]


def _fill_links(text: str) -> str:
    for key, source in facts()["sources"].items():
        text = text.replace("{" + key + "}", source["url"])
    return text


def _build_turns(raw_turns: list[dict]) -> list[Turn]:
    turns: list[Turn] = []
    for raw in raw_turns:
        user = raw["user"]
        if raw.get("filler_chars"):
            repeats = raw["filler_chars"] // len(_FILLER) + 1
            user = (_FILLER * repeats)[:raw["filler_chars"]] + " " + user
        copies = raw.get("repeat", 1)
        for n in range(copies):
            turns.append(Turn(
                id=raw["id"] if copies == 1 else f"{raw['id']}_{n + 1}",
                user=user,
                expect=raw.get("expect", []),
                reference=_fill_links(raw.get("reference", "")).strip(),
                tags=raw.get("tags", []),
                allow_status=raw.get("allow_status", [200]),
                abuse=raw.get("abuse", False),
                burst=raw.get("burst", 0),
                cooldown_s=raw.get("cooldown_s", 0.0),
            ))
    return turns


@lru_cache(maxsize=None)
def load_personas() -> tuple[Persona, ...]:
    personas = []
    for path in sorted(PERSONA_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        personas.append(Persona(
            id=raw["id"], name=raw["name"], label=raw["label"], kind=raw["kind"],
            who=raw["who"].strip(), question_types=raw.get("question_types", []),
            turns=_build_turns(raw["turns"]),
        ))
    return tuple(personas)


def get_persona(persona_id: str) -> Persona:
    for persona in load_personas():
        if persona.id == persona_id:
            return persona
    raise KeyError(persona_id)
