"""Turn the words of a Spanish question into the English words the pages use.

The 7 pages are in English and retrieval matches words, so "cuanto cuesta"
or "comidas" would find nothing. Before searching, accents are removed and
common Spanish words are swapped for their English equivalent; Spanish
filler words are dropped. English text passes through unchanged.
"""
from __future__ import annotations

import re
import unicodedata

# Spanish word (without accents) -> English word used on the pages.
SPANISH = {
    "cuanto": "much", "cuanta": "much", "cuantos": "much", "cuesta": "cost", "cuestan": "cost",
    "costo": "cost", "costos": "cost", "coste": "cost", "precio": "price", "precios": "price",
    "pagar": "pay", "dolar": "dollar", "dolares": "dollars", "barato": "cheaper", "caro": "expensive",
    "incluye": "include", "incluyen": "include", "incluido": "included", "incluida": "included",
    "incluidos": "included", "incluidas": "included", "incluir": "include", "cubre": "cover",
    "adicional": "additional", "adicionales": "additional",
    "comida": "meal", "comidas": "meals", "alimentacion": "food", "alimentos": "food",
    "hospitalizacion": "inpatient", "hospitalizado": "inpatient", "internado": "inpatient",
    "ambulatorio": "outpatient", "alojamiento": "accommodation", "hospedaje": "accommodation",
    "habitacion": "room", "cuarto": "room", "vuelo": "flight", "aeropuerto": "airport",
    "transporte": "transport", "traslado": "transport", "semana": "week", "semanas": "weeks",
    "dia": "day", "dias": "days", "tratamiento": "treatment", "tratamientos": "treatments",
    "terapia": "therapy", "terapias": "therapies", "medico": "doctor", "medicos": "doctors",
    "doctores": "doctors", "clinica": "clinic", "clinicas": "clinics",
    "suprarrenal": "adrenal", "suprarrenales": "adrenal", "paquete": "package", "paquetes": "packages",
    "programa": "program", "programas": "programs", "testimonio": "testimonial",
    "testimonios": "testimonials", "opiniones": "reviews", "resena": "review", "resenas": "reviews",
    "resultados": "results", "efectos": "effects", "secundarios": "side", "quimioterapia": "chemotherapy",
    "radiacion": "radiation", "inmunoterapia": "immunotherapy", "presion": "pressure",
    "sangre": "blood", "medicamentos": "medications", "medicinas": "medications",
    "seguimiento": "follow", "consulta": "consultation", "duracion": "duration",
    "comparar": "compare", "promedio": "average", "otras": "other", "otros": "other",
    "analisis": "lab", "laboratorio": "lab", "estudios": "tests", "pruebas": "tests",
}

# Spanish filler words, dropped so they don't match Spanish clinic names on the pages.
SPANISH_STOPWORDS = set("""el la los las de del al y o en es para con por un una unos unas mi mis su sus
lo le les se que eso esto esta este como si hay me nos te ustedes usted pero mas muy ya tiene tienen""".split())


def fold_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def to_english(text: str) -> str:
    """Lowercase, accent-free text with known Spanish words replaced and filler words dropped."""
    def swap(match: re.Match) -> str:
        word = match.group(0)
        return "" if word in SPANISH_STOPWORDS else SPANISH.get(word, word)
    return re.sub(r"[a-z]+", swap, fold_accents(text).lower())
