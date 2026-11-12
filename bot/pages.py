"""The 7 PlacidWay pages the bot is allowed to know about."""
from __future__ import annotations

from dataclasses import dataclass

BASE = "https://www.placidway.com"


@dataclass(frozen=True)
class Page:
    key: str      # short name, used for file names and in the index
    url: str
    title: str    # how the page is introduced to the model
    topics: tuple[str, ...] = ()   # regex fragments: words in a question that point at this page


PAGES = [
    Page("profile", f"{BASE}/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
         "ITC (Immunity Therapy Center) clinic profile"),   # the default page: no topic words
    Page("pkg_adenocarcinoma",
         f"{BASE}/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
         "Alternative Adenocarcinoma Cancer Treatment package", ("adenocarcinoma", "adeno")),
    Page("pkg_adrenal",
         f"{BASE}/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
         "Alternative Adrenal Cancer Treatment package", ("adrenal",)),
    Page("pkg_anal",
         f"{BASE}/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
         "Alternative Anal Cancer Treatment package", ("anal",)),
    Page("videos", f"{BASE}/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
         "ITC videos and testimonials", ("video", "testimonial", "temoign", "watch")),
    Page("price_list", f"{BASE}/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
         "ITC price list", ("price list", "pricelist", "procedures")),
    Page("comparison", f"{BASE}/search-medical-pricings/Alternative-Medicine/All/1",
         "Alternative medicine price comparison across clinics",
         ("compare", "comparison", "other clinic", "other countries", "average",
          "ayurved", "panchakarma", "naturopath", "acupunct",     # therapies only this page lists
          # "cheaper" alone often means "the cheaper of the options you gave", so only these forms
          r"cheaper (in|at|abroad|elsewhere|than|somewhere|anywhere)")),
]

PAGE_BY_KEY = {page.key: page for page in PAGES}

# Questions about the clinic itself (founder, doctors, location) are answered from its profile.
# These words count only in the newest message: such a question is a one-off, and
# the package discussed before it stays the subject of later follow-ups.
CLINIC_PAGE = "profile"
CLINIC_TOPICS = (r"found(ed|er|ing)\b", r"doctors?\b", r"physicians?\b", "medical director",
                 r"staff\b", "medical team", "who runs", "owner", "accredit", r"located\b", r"location\b")
COMPARISON_PAGE = "comparison"
