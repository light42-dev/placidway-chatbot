"""Text extraction details of scripts/ingest.py, and what they must have produced in data/. No network needed."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ingest", ROOT / "scripts" / "ingest.py")
ingest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)


def test_a_card_price_moves_below_its_own_title():
    lines = ["# Packages", "Price starting from $4,500", "# Course in Tbilisi", "Tbilisi,Georgia",
             "# Program in Murter", "Murter,Croatia", "Price starting from $24,000", "# Integrative Cancer Treatment"]
    assert ingest.attach_card_prices(lines) == [
        "# Packages", "# Course in Tbilisi", "Price starting from $4,500", "Tbilisi,Georgia",
        "# Program in Murter", "Murter,Croatia", "# Integrative Cancer Treatment", "Price starting from $24,000"]


def test_other_price_lines_stay_where_they_are():
    lines = ["# Out-Patient Program", "Total cost $18,995", "Price starting from $64", "Share this listing"]
    assert ingest.attach_card_prices(lines) == lines


def test_saved_comparison_page_gives_each_package_its_own_price():
    """Checked by hand against the live page on 2026-11-13."""
    lines = (ROOT / "data" / "pages" / "comparison.txt").read_text(encoding="utf-8").splitlines()
    price_under = {lines[i - 1]: line for i, line in enumerate(lines) if ingest.CARD_PRICE.match(line)}
    assert price_under["# Integrative Cancer Treatment"] == "Price starting from $24,000"
    assert price_under["# Local Treatment Course in Tbilisi, Georgia by Eliava"] == "Price starting from $4,500"
    wolistic = next(title for title in price_under if title.startswith("# Ozone Therapy Package at Wolistic"))
    assert price_under[wolistic] == "Price starting from $1,500"
