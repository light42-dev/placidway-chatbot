"""Answer "is there a video about <condition>?" from the full list of video titles.

The videos page is a long list of titles (about 120), cut into many small
passages, so keyword search only ever shows the model a handful of them. When
a question asks about videos of a condition, this module checks every title in
code and hands the model one short passage: the matching titles, or the fact
that no title mentions that condition. A "no" is then grounded in the whole
page, not in the few passages that happened to be retrieved.
"""
from __future__ import annotations

import re
from functools import lru_cache

from ..config import ROOT
from .index import Passage

ASKS_FOR_VIDEOS = re.compile(r"vid[eé]o|t[eé]moign|testimon|stor(y|ies)|histoire|historia", re.I)
MAX_TITLES = 25             # keeps the passage under about 1,500 characters

# Conditions as the titles name them (English), with the words a visitor may use
# for them in French or Spanish. Each word is matched as a whole word.
CONDITIONS = {
    "breast": ("breast", "sein", "seins", "mama", "seno", "senos"),
    "lung": ("lung", "poumon", "poumons", "pulmonaire", "pulmón", "pulmon", "pulmonar"),
    "prostate": ("prostate", "próstata", "prostata"),
    "colon": ("colon", "côlon"),
    "colorectal": ("colorectal", "colorrectal"),
    "rectal": ("rectal", "rectum", "recto"),
    "anal": ("anal", "anus"),
    "adrenal": ("adrenal", "surrénale", "surrénales", "suprarrenal"),
    "adenocarcinoma": ("adenocarcinoma", "adénocarcinome"),
    "pancreatic": ("pancreatic", "pancreas", "pancréas", "páncreas"),
    "liver": ("liver", "foie", "hígado", "higado"),
    "brain": ("brain", "cerveau", "cerebro"),
    "bladder": ("bladder", "vessie", "vejiga"),
    "stomach": ("stomach", "estomac", "estómago"),
    "gastric": ("gastric", "gastrique", "gástrico"),
    "esophageal": ("esophageal", "oesophage", "œsophage", "esófago"),
    "ovarian": ("ovarian", "ovaire", "ovario"),
    "cervical": ("cervical", "cervix"),
    "kidney": ("kidney", "rein", "riñón"),
    "skin": ("skin", "peau", "piel", "melanoma", "mélanome"),
    "lymphoma": ("lymphoma", "lymphome", "linfoma", "hodgkin"),
    "leukemia": ("leukemia", "leucémie", "leucemia", "aml"),
    "myeloma": ("myeloma", "myélome", "mieloma"),
    "sarcoma": ("sarcoma", "sarcome"),
    "thyroid": ("thyroid", "thyroïde", "tiroides"),
    "uterine": ("uterine", "utérus", "útero"),
    "neuroendocrine": ("neuroendocrine", "carcinoid"),
    "lyme": ("lyme",),
}

# Words that make a title long without saying anything about the patient.
_TITLE_NOISE = re.compile(
    r"\s*\b(in|at|by|with|from)?\s*(Tijuana|Mexico|ITC Immunity Therapy Center|Immunity Therapy Center"
    r"|ITC)\b[,.]?|\bAlternative\b", re.I)


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-zà-ÿœ]+", text.lower()))


@lru_cache(maxsize=1)
def video_titles() -> tuple[str, ...]:
    """The video titles on the videos page, in page order, shortened."""
    path = ROOT / "data" / "pages" / "videos.txt"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    titles = []
    for line in lines:
        if line.startswith("# Recent Reviews"):
            break                       # the reviews below are not videos
        if line.startswith("# ") and not line.startswith(("# ITC ", "# About ")):
            titles.append(" ".join(_TITLE_NOISE.sub(" ", line[2:]).split()).strip(" ,.:-"))
    return tuple(titles)


def asked_conditions(question: str) -> list[str]:
    """The conditions (English title words) named in the question."""
    words = _words(question)
    return [name for name, aliases in CONDITIONS.items() if words & set(aliases)]


def video_passage(question: str) -> Passage | None:
    """A passage listing the videos about the conditions asked for, or None if not a video question."""
    if not ASKS_FOR_VIDEOS.search(question):
        return None
    conditions = asked_conditions(question)
    titles = video_titles()
    if not conditions or not titles:
        return None
    lines = []
    for condition in conditions:
        matching = [t for t in titles if condition in _words(t)]
        if matching:
            shown = "\n".join(f"- {t}" for t in matching[:MAX_TITLES])
            more = f"\n(and {len(matching) - MAX_TITLES} more)" if len(matching) > MAX_TITLES else ""
            lines.append(f"{len(matching)} of the {len(titles)} video titles mention {condition}:\n{shown}{more}")
        else:
            lines.append(f"Not listed: none of the {len(titles)} video titles mention {condition}.")
    return Passage("videos", "Videos on the ITC videos page, checked title by title.\n" + "\n".join(lines))
