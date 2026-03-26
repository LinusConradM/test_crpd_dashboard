from collections import Counter
import re

import numpy as np
import pandas as pd
import streamlit as st

from src.data_loader import MODEL_DICT


# Pre-compile regex patterns for better performance
_COMPILED_PATTERNS_CACHE = {}


def _get_compiled_pattern(phrase):
    """Get or create a compiled regex pattern for a phrase."""
    if phrase not in _COMPILED_PATTERNS_CACHE:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        _COMPILED_PATTERNS_CACHE[phrase] = re.compile(pattern, re.IGNORECASE)
    return _COMPILED_PATTERNS_CACHE[phrase]


# English stopwords (common words to exclude from frequency analysis)
STOPWORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "might",
    "more",
    "most",
    "must",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
    "could",
    "may",
    "also",
    "however",
    "therefore",
    "thus",
    "hence",
    "moreover",
    "furthermore",
    "nevertheless",
    "nonetheless",
    "meanwhile",
    "otherwise",
    "whereas",
    "yet",
    "still",
    "already",
    "always",
    "never",
    "often",
    "sometimes",
    "usually",
    "generally",
    "particularly",
    "especially",
    "specifically",
    "namely",
    "including",
    "within",
    "without",
    "upon",
    "via",
    "per",
    "amongst",
    "toward",
    "towards",
    "throughout",
    "across",
    "along",
    "around",
    "behind",
    "beside",
    "besides",
    "beyond",
    "near",
    "onto",
    "since",
    "till",
    "unless",
    "unlike",
    "whether",
    "whose",
    "whoever",
    "whomever",
    "whatever",
    "whichever",
    "wherever",
    "whenever",
    "indeed",
    "rather",
    "quite",
    "fairly",
    "pretty",
    "much",
    "many",
    "several",
    "various",
    "certain",
    "another",
    "others",
    "either",
    "neither",
    "every",
    "less",
    "least",
    "little",
    "enough",
    "self",
    "selves",
    "one",
    "two",
    "three",
    "first",
    "second",
    "third",
    "last",
    "next",
    "previous",
    "following",
    "former",
    "latter",
    "earlier",
    "later",
}

# Domain-specific stopwords for CRPD documents (procedural/structural terms)
DOMAIN_STOPWORDS = {
    "committee",
    "state",
    "party",
    "article",
    "paragraph",
    "report",
    "section",
    "chapter",
    "annex",
    "appendix",
    "page",
    "document",
    "number",
    "date",
    "year",
    "month",
    "day",
    "act",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "crpd",
    "convention",
    "united",
    "nations",
    "general",
    "assembly",
    "session",
    "meeting",
    "agenda",
    "item",
    "resolution",
    "decision",
    "recommendation",
    "note",
    "letter",
    "communication",
    "submission",
    "reply",
    "response",
    "observation",
    "concluding",
    "initial",
    "periodic",
    "supplementary",
    "additional",
    "follow",
    "followup",
    "pursuant",
    "accordance",
    "regard",
    "respect",
    "concerning",
    "regarding",
    "relation",
    "reference",
    "referred",
    "refers",
    "referring",
    "mentioned",
    "noted",
    "stated",
    "indicated",
    "provided",
    "reported",
    "informed",
    "requested",
    "recommended",
    "urged",
    "called",
    "invited",
    "welcomed",
    "acknowledged",
    "recognized",
    "emphasized",
    "stressed",
    "reiterated",
    "recalled",
    "reaffirmed",
    "confirmed",
    "expressed",
    "took",
    "made",
    "adopted",
    "approved",
    "shall",
    "should",
    "must",
    "might",
    "can",
    "could",
    "would",
    "will",
    "need",
    "needs",
    "ensure",
    "ensuring",
    "ensured",
    "take",
    "taking",
    "taken",
    "make",
    "making",
    "provide",
    "providing",
    "given",
    "give",
    "giving",
    "implement",
    "implementing",
    "implemented",
    "establish",
    "establishing",
    "established",
    "develop",
    "developing",
    "developed",
    "promote",
    "promoting",
    "promoted",
    "strengthen",
    "strengthening",
    "strengthened",
    "improve",
    "improving",
    "improved",
    "enhance",
    "enhancing",
    "enhanced",
    "increase",
    "increasing",
    "increased",
    "continue",
    "continuing",
    "continued",
    "maintain",
    "maintaining",
    "maintained",
    "support",
    "supporting",
    "supported",
    "facilitate",
    "facilitating",
    "facilitated",
    "encourage",
    "encouraging",
    "encouraged",
    "address",
    "addressing",
    "addressed",
    "consider",
    "considering",
    "considered",
    "review",
    "reviewing",
    "reviewed",
    "monitor",
    "monitoring",
    "monitored",
    "evaluate",
    "evaluating",
    "evaluated",
    "assess",
    "assessing",
    "assessed",
}

# Procedural / formulaic UN terms that leak into topic models
_PROCEDURAL_STOPWORDS = {
    "please",
    "concerned",
    "notes",
    "welcomes",
    "urges",
    "recalls",
    "recommends",
    "regrets",
    "appreciates",
    "observations",
    "measures",
    "appropriate",
    "particular",
    "also",
    "including",
    "specific",
    "relevant",
    "effective",
    "necessary",
    "available",
    "Republic",
    "republic",
    "peoples",
    "people",
    "government",
    "ministry",
    "minister",
    "legislation",
    "law",
    "laws",
    "programme",
    "programs",
    "national",
    "federal",
    "provincial",
    "municipal",
    "conditions",
    "thereof",
    "herein",
    "therein",
    "whereby",
    "whereas",
    "furthermore",
    "moreover",
    "notwithstanding",
    "indicate",
    "indicated",
    "raised",
    "arm",
    "arg",
    "bol",
    "bra",
    "col",
    "ecu",
    "geo",
    "ira",
    "irn",
    "isl",
    "mac",
    "mex",
    "nic",
    "pan",
    "per",
    "ven",
    "el",
    "de",
    "la",
    "des",
    "les",
    "governmental",
    "non",
    "pre",
    "sub",
    "replies",
    "bureau",
    "activities",
    "commission",
    "department",
    "sar",
    "provides",
    "inform",
    "lack",
    "ordinance",
    "institute",
    "art",
    "article",
    "articles",
    "list",
    "lists",
    "issues",
    "questions",
    "information",
    "action",
    "actions",
    "advancement",
    "association",
    "decree",
    "decrees",
    "presidential",
    "family",
    "families",
    "insurance",
    "examination",
    "organizations",
    "representative",
    "representatives",
    # --- Round 2: tighten bigram quality ---
    # Procedural verbs / report boilerplate
    "reads",
    "follows",
    "following",
    "pursuant",
    "accordance",
    "regard",
    "regarding",
    "respect",
    "concerning",
    "referred",
    "refers",
    "reference",
    "noted",
    "ensure",
    "ensures",
    "ensuring",
    "adopted",
    "adopting",
    "implementation",
    "implemented",
    "implementing",
    # Institutional / generic titles
    "office",
    "officer",
    "officers",
    "commissioner",
    "agency",
    "agencies",
    "associations",
    "council",
    "committee",
    "secretariat",
    "authority",
    "authorities",
    "directorate",
    "delegation",
    # Generic modifiers that pair with everything
    "special",
    "general",
    "various",
    "certain",
    "several",
    "different",
    "additional",
    "related",
    "based",
    "level",
    "levels",
    "areas",
    "area",
    "sector",
    "sectors",
    "rate",
    "rates",
    "status",
    "public",
    "private",
    "framework",
    "frameworks",
    "services",
    "service",
    "system",
    "systems",
    "process",
    "processes",
    "policy",
    "policies",
    "plan",
    "plans",
    "strategy",
    "period",
    "code",
    "codes",
    "order",
    "report",
    "reports",
    "reporting",
    "state",
    "states",
    "party",
    "parties",
    "number",
    "total",
    "year",
    "years",
    "cent",
    "percentage",
    # --- Round 3: tighten further ---
    # Generic time / quantity modifiers
    "term",
    "long",
    "short",
    "approximately",
    "currently",
    "recently",
    "previously",
    # Procedural verbs / connectives
    "matters",
    "matter",
    "relating",
    "respective",
    "given",
    "taken",
    "made",
    "carried",
    # Institutional / bureaucratic
    "affairs",
    "bank",
    "fund",
    "funds",
    "institution",
    "institutions",
    "division",
    "section",
    "unit",
    "board",
    "body",
    "bodies",
    # Currency / financial noise
    "pesos",
    "dollars",
    "euros",
    "francs",
    "rupees",
    "dinars",
    "currency",
    # CRPD-ubiquitous words that pair with everything generically
    "protection",
    "participation",
    "opportunities",
    "opportunity",
    "development",
    "labour",
    "labor",
    "place",
    "book",
    "books",
    # --- Round 4: final tightening ---
    # Latin / legal boilerplate
    "inter",
    "alia",
    "facto",
    "supra",
    "ibid",
    "vis",
    # Procedural verbs / phrases
    "like",
    "mention",
    "mentioned",
    "mentioning",
    "raise",
    "raising",
    "note",
    "consider",
    "considered",
    "considering",
    "regards",
    "receive",
    "received",
    "receiving",
    "submit",
    "submitted",
    "submitting",
    "request",
    "requested",
    "requesting",
    "provide",
    "provided",
    "providing",
    # Generic modifiers / institutional
    "economic",
    "principle",
    "principles",
    "confederation",
    "federation",
    "awareness",
    "higher",
    "quality",
    "equal",
    "basis",
    "inclusion",
    "security",
    "solidarity",
    # --- Round 5: publication / gazette / institutional ---
    "official",
    "gazette",
    "gazettes",
    "gaceta",
    "oficial",
    "published",
    "publication",
    "publications",
    "publishing",
    # Institutional / bureaucratic (round 5)
    "establishment",
    "establishments",
    "remit",
    "functioning",
    "regional",
    "formats",
    "format",
    "county",
    "counties",
    "municipality",
    "municipalities",
    "upper",
    "secondary",
    "primary",
    "lower",
    "mission",
    "missions",
    "councils",
    "organisation",
    "organisations",
    "organization",
    # Sustainable development goals (procedural)
    "sustainable",
    "goal",
    "goals",
    # Generic demographic pairings
    "young",
    "men",
    "boys",
    "male",
    "female",
    "care",
    "medical",
    # PDF artifacts — statute/reference codes
    "sfs",
    "crpd",
    "opt",
    "crc",
    "cedaw",
    "iccpr",
    "icescr",
    "cat",
    "cerd",
    "cmw",
    "ced",
    # Procedural fragments that leak into bigrams and topics
    "pertaining",
    "bearing",
    "recommended",
    "recommendation",
    "recommendations",
    "pdea",
    # Common proper names that leak from reports
    "jose",
    "gregorio",
    "hernandez",
    "bolivar",
    "chavez",
    "morales",
    # --- Round 6: LDA global-model cleanup ---
    # Generic / ubiquitous CRPD vocabulary that drowns topic labels
    "country",
    "countries",
    "constitution",
    "constitutional",
    "adopt",
    "adoption",
    "concern",
    "concerns",
    "according",
    "accordingly",
    "centre",
    "centres",
    "center",
    "centers",
    "union",
    "unions",
    "pwd",
    "pwds",
    "programmes",
    "program",
    "rural",
    "urban",
    "individual",
    "individuals",
    "european",
    "african",
    "asian",
    "pacific",
    "caribbean",
    "latin",
    "arab",
    "western",
    "eastern",
    "southern",
    "northern",
    "central",
    # Additional procedural / boilerplate
    "implement",
    "measure",
    "ensured",
    "promote",
    "promoted",
    "promoting",
    "promotion",
    "protect",
    "protected",
    "protecting",
    "provision",
    "provisions",
    "require",
    "required",
    "requires",
    "requirement",
    "requirements",
    "establish",
    "established",
    "establishing",
    "include",
    "included",
    "includes",
    "particularly",
    "specifically",
    "addition",
    "however",
    "therefore",
    "within",
    "access",
    "paragraph",
    "paragraphs",
    "convention",
    "committees",
    "reported",
    "governments",
    "international",
    "act",
    "acts",
    "legal",
    "right",
    "rights",
    "persons",
    "person",
    "children",
    "child",
    "women",
    "woman",
    "girls",
    "girl",
    "disability",
    "disabilities",
    "disabled",
    "social",
    "society",
    "support",
    "education",
    "health",
    "work",
    "employment",
    "situation",
    "mechanism",
    "mechanisms",
    "activity",
    # --- Round 7: NMF topic cleanup (LDA/NMF-only) ---
    "population",
    "comment",
    "comments",
    "case",
    "cases",
    "field",
    "fields",
    "help",
    "responsible",
    "responsibility",
    "project",
    "projects",
    "citizens",
    "citizen",
    "involvement",
    "involved",
    "involve",
    "learning",
    "welfare",
    "taking",
    "take",
    "make",
    "among",
    "well",
    "may",
    "shall",
    "must",
    "would",
    "could",
    "should",
    "many",
    "every",
    "part",
    "full",
    "fully",
    "new",
    "current",
    "recent",
    "way",
    "ways",
    "form",
    "forms",
    "type",
    "types",
    "important",
    "main",
    "major",
    "key",
    "need",
    "needs",
    "use",
    "used",
    "using",
    "result",
    "results",
    "able",
    "still",
    "often",
    "even",
    "example",
    "call",
    "called",
    "calls",
    "whether",
    "view",
    "views",
    "due",
    "terms",
    "continue",
    "continued",
    "range",
    "sufficient",
    "step",
    "steps",
    # --- Round 8: NMF artifact / procedural cleanup ---
    # Abbreviation artifacts from UN documents
    "uncrpd",
    "ext",
    "para",
    "paras",
    "ref",
    "annex",
    "doc",
    "sess",
    "supp",
    "vol",
    "rev",
    "corr",
    "add",
    # Procedural verbs that survive TF-IDF
    "recalling",
    "recalled",
    "recall",
    "explain",
    "explained",
    "explains",
    "explaining",
    "describe",
    "described",
    "describes",
    "describing",
    "updated",
    "update",
    "updates",
    "updating",
    "establishes",
    "noting",
    "indicates",
    "indicating",
    "address",
    "addressed",
    "addresses",
    "addressing",
    "requests",
    "urge",
    "urged",
    "urging",
    "welcome",
    "welcomed",
    "welcoming",
    "recognize",
    "recognized",
    "recognizes",
    "recognizing",
    "acknowledge",
    "acknowledged",
    "acknowledges",
    "acknowledging",
    "express",
    "expressed",
    "expresses",
    "expressing",
    "reaffirm",
    "reaffirmed",
    "reaffirms",
    "reaffirming",
    # Generic adjectives / nouns that dilute topics
    "absence",
    "insufficient",
    "patient",
    "patients",
    "pupils",
    "pupil",
    "bill",
    "bills",
    "district",
    "districts",
    "affected",
    "affecting",
    "affects",
    "effect",
    "effectively",
    "adequate",
    "significant",
    "comprehensive",
    "existing",
    "applicable",
    "prior",
    # --- Round 9: committee/LOI formulaic verbs ---
    "stipulates",
    "stipulate",
    "stipulated",
    "stipulating",
    "organized",
    "organize",
    "organizes",
    "organizing",
    "specify",
    "specifies",
    "specified",
    "specifying",
    "clarify",
    "clarifies",
    "clarified",
    "clarifying",
    "commends",
    "commend",
    "commended",
    "commending",
    "details",
    "detailed",
    "detailing",
    "question",
    "questioned",
    "questioning",
    "answer",
    "answers",
    "answered",
    "answering",
    "allowance",
    "allowances",
    "provinces",
    "province",
    "regret",
    "regretting",
    "appreciate",
    "appreciated",
    "appreciating",
    "encourages",
    "encourage",
    "encouraged",
    "encouraging",
    "deplores",
    "deplore",
    "deplored",
    "deploring",
    "reiterates",
    "reiterate",
    "reiterated",
    "reiterating",
    "invites",
    "invite",
    "invited",
    "inviting",
}

# Country names + demonyms that leak into topic models — auto-generated from pycountry
_DEMONYM_SUFFIXES = ("an", "ian", "ese", "ish", "ic", "i", "er")
try:
    import pycountry as _pyc

    _COUNTRY_STOPWORDS = set()
    for _c in _pyc.countries:
        _name_lower = _c.name.lower()
        # Add country name words (3+ chars)
        for _w in _name_lower.replace(",", " ").replace("(", " ").replace(")", " ").split():
            if len(_w) > 2:
                _COUNTRY_STOPWORDS.add(_w)
        # Add ISO alpha-3 codes (lowercased)
        if hasattr(_c, "alpha_3"):
            _COUNTRY_STOPWORDS.add(_c.alpha_3.lower())
        # Generate common demonym forms (e.g. uruguay → uruguayan)
        _base = _name_lower.split(",")[0].split("(")[0].strip().split()[-1]
        if len(_base) > 3:
            for _suf in _DEMONYM_SUFFIXES:
                # "chile" → "chilean", "japan" → "japanese", etc.
                _COUNTRY_STOPWORDS.add(_base + _suf)
                if _base.endswith("a"):
                    _COUNTRY_STOPWORDS.add(_base[:-1] + _suf)
                if _base.endswith("e"):
                    _COUNTRY_STOPWORDS.add(_base[:-1] + _suf)
                if _base.endswith("y"):
                    _COUNTRY_STOPWORDS.add(_base[:-1] + _suf)
    # Irregular demonyms that suffix rules miss
    _COUNTRY_STOPWORDS.update(
        {
            "honduran",
            "monegasque",
            "vietnamese",
            "czech",
            "german",
            "mexican",
            "peruvian",
            "british",
            "french",
            "dutch",
            "swiss",
            "danish",
            "finnish",
            "swedish",
            "norwegian",
            "polish",
            "spanish",
            "portuguese",
            "turkish",
            "greek",
            "cypriot",
            "maltese",
            "slovene",
            "slovenian",
            "croatian",
            "serbian",
            "bosnian",
            "kosovar",
            "albanian",
            "macedonian",
            "montenegrin",
            "senegalese",
            "congolese",
            "togolese",
            "djiboutian",
            "burundian",
            "rwandan",
            "kenyan",
            "ugandan",
            "tanzanian",
            "ethiopian",
            "eritrean",
            "somali",
            "sudanese",
            "egyptian",
            "libyan",
            "tunisian",
            "algerian",
            "moroccan",
            "ghanaian",
            "nigerian",
            "cameroonian",
            "ivorian",
            "malian",
            "nigerien",
            "beninese",
            "filipino",
            "thai",
            "burmese",
            "cambodian",
            "laotian",
            "indonesian",
            "malaysian",
            "singaporean",
            "taiwanese",
            "korean",
            "mongolian",
            "nepalese",
            "nepali",
            "bangladeshi",
            "sri",
            "lankan",
            "afghan",
            "iraqi",
            "syrian",
            "lebanese",
            "jordanian",
            "emirati",
            "qatari",
            "bahraini",
            "kuwaiti",
            "omani",
            "yemeni",
            "saudi",
            "palestinian",
            "israeli",
            "guatemalan",
            "salvadoran",
            "nicaraguan",
            "costa",
            "rican",
            "panamanian",
            "colombian",
            "venezuelan",
            "ecuadorian",
            "bolivian",
            "paraguayan",
            "argentinian",
            "argentine",
            # Missing demonyms caught during quality review
            "irish",
            "maldivian",
            "canadians",
            "canadian",
            "americans",
            "american",
            "australians",
            "australian",
            "europeans",
            "european",
            "africans",
            "african",
            "asians",
            "asian",
            "cubans",
            "cuban",
            "haitian",
            "jamaican",
            "trinidadian",
            "barbadian",
            "belizean",
            "guyanese",
            "surinamese",
            "chilean",
            "uruguayan",
            "brazilian",
            "dominican",
            "puerto",
        }
    )
    # ------------------------------------------------------------------
    # Sub-national administrative divisions — auto-generated from
    # pycountry.subdivisions (ISO 3166-2).  Covers ~5,000 regions for
    # all 249 countries systematically, replacing manual per-country lists.
    # ------------------------------------------------------------------
    import unicodedata as _ud

    def _ascii_fold(s):
        """Normalize accented chars to ASCII (e.g. Åland → aland)."""
        return _ud.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()

    for _subdiv in _pyc.subdivisions:
        _sub_name = _subdiv.name.lower()
        _sub_ascii = _ascii_fold(_subdiv.name)
        # Add individual words (≥4 chars) from subdivision names — both
        # original and ASCII-folded to catch "åland" → "aland" etc.
        for _variant in (_sub_name, _sub_ascii):
            for _w in (
                _variant.replace(",", " ")
                .replace("(", " ")
                .replace(")", " ")
                .replace("-", " ")
                .replace("'", " ")
                .split()
            ):
                if len(_w) >= 4:
                    _COUNTRY_STOPWORDS.add(_w)
    # General geographic terms not in ISO 3166-2
    _COUNTRY_STOPWORDS.update(
        {
            "province",
            "provinces",
            "territory",
            "territories",
            "canton",
            "cantons",
            "prefecture",
            "prefectural",
            "prefectures",
            "governorate",
            "governorates",
            "municipality",
            "municipalities",
            "district",
            "districts",
            "borough",
            "boroughs",
            "county",
            "counties",
            "parish",
            "parishes",
            "oblast",
            "oblasts",
            "voivodeship",
        }
    )
    # Capital cities and major cities — geography, not policy content.
    _COUNTRY_STOPWORDS.update(
        {
            "abuja",
            "accra",
            "algiers",
            "amman",
            "amsterdam",
            "ankara",
            "antananarivo",
            "ashgabat",
            "astana",
            "asuncion",
            "athens",
            "baghdad",
            "baku",
            "bamako",
            "bangalore",
            "bangkok",
            "banjul",
            "beijing",
            "beirut",
            "belgrade",
            "berlin",
            "bern",
            "bishkek",
            "bogota",
            "brasilia",
            "bratislava",
            "brazzaville",
            "brussels",
            "bucharest",
            "budapest",
            "cairo",
            "canberra",
            "caracas",
            "casablanca",
            "chennai",
            "chisinau",
            "colombo",
            "conakry",
            "copenhagen",
            "dakar",
            "damascus",
            "dhaka",
            "dodoma",
            "doha",
            "dublin",
            "freetown",
            "gitega",
            "hanoi",
            "harare",
            "havana",
            "helsinki",
            "hulhumale",
            "hyderabad",
            "islamabad",
            "jakarta",
            "jerusalem",
            "kabul",
            "kampala",
            "karachi",
            "kathmandu",
            "khartoum",
            "kigali",
            "kingston",
            "kolkata",
            "kyiv",
            "libreville",
            "lilongwe",
            "lima",
            "lisbon",
            "ljubljana",
            "lome",
            "london",
            "luanda",
            "lusaka",
            "madrid",
            "managua",
            "manama",
            "manila",
            "maputo",
            "marrakech",
            "maseru",
            "minsk",
            "mombasa",
            "monrovia",
            "montevideo",
            "moroni",
            "moscow",
            "muscat",
            "nairobi",
            "naypyidaw",
            "ndjamena",
            "niamey",
            "nicosia",
            "nouakchott",
            "oslo",
            "ottawa",
            "ouagadougou",
            "paramaribo",
            "paris",
            "podgorica",
            "prague",
            "praia",
            "pretoria",
            "quito",
            "rabat",
            "ramallah",
            "riga",
            "riyadh",
            "rome",
            "safi",
            "sanaa",
            "santiago",
            "sarajevo",
            "seoul",
            "skopje",
            "sofia",
            "stockholm",
            "sucre",
            "suva",
            "tallinn",
            "tashkent",
            "tbilisi",
            "tegucigalpa",
            "tehran",
            "tirana",
            "tokyo",
            "tripoli",
            "tunis",
            "ulaanbaatar",
            "valletta",
            "vienna",
            "vientiane",
            "vilnius",
            "warsaw",
            "wellington",
            "windhoek",
            "yaounde",
            "yerevan",
            "zagreb",
        }
    )
except ImportError:
    _COUNTRY_STOPWORDS = set()

# Generic high-frequency English words that survive domain stopwords but carry
# no analytical value for distinctive-language analysis.
_GENERIC_ENGLISH_STOPWORDS = {
    "time",
    "group",
    "local",
    "works",
    "basic",
    "designed",
    "based",
    "used",
    "made",
    "given",
    "take",
    "taken",
    "make",
    "include",
    "including",
    "included",
    "related",
    "according",
    "since",
    "within",
    "upon",
    "part",
    "well",
    "also",
    "addition",
    "case",
    "cases",
    "form",
    "area",
    "areas",
    "level",
    "high",
    "number",
    "place",
    "order",
    "line",
    "following",
    "regard",
    "regards",
    "various",
    "general",
    "total",
    "main",
    "different",
    "certain",
    "particular",
    "specific",
    "ends",
    "gaining",
    "profound",
    "beautiful",
    "fort",
    "large",
    "small",
    "long",
    "full",
    "early",
    "late",
    "open",
    "close",
    "closed",
    "wide",
    "held",
    "received",
    "carried",
    "provided",
    "established",
    "noted",
    "concerned",
    "adopted",
    "considered",
    "submitted",
    "referred",
    "presented",
    "indicated",
    "mentioned",
    "stated",
    "reported",
    # Round 2: generic adverbs/adjectives flagged by text analyst
    "hopefully",
    "undoubtedly",
    "modest",
    "vigorous",
    "foregoing",
    "pertain",
    "subtotal",
    "dozen",
    "seas",
    "merely",
    "fairly",
    "greatly",
    "somewhat",
    "entirely",
    "virtually",
    "approximately",
    "currently",
    "previously",
    "recently",
    "subsequently",
    "respectively",
    "primarily",
    "particularly",
    # Round 3: discourse markers, legal filler, function-adjacent words
    "furthermore",
    "nevertheless",
    "notwithstanding",
    "thereof",
    "herein",
    "therein",
    "whereby",
    "wherein",
    "henceforth",
    "accordingly",
    "consequently",
    "moreover",
    "nonetheless",
    "likewise",
    "meanwhile",
    "otherwise",
    "thereafter",
    "beforehand",
    "hereunder",
    "thereto",
    "hereto",
    "herewith",
    "forthwith",
}

# Combine all stopwords
# BIGRAM_STOPWORDS: lighter set for bigram extraction (keyness handles most noise)
# ALL_STOPWORDS: aggressive set for NMF/topic modeling — removes CRPD-ubiquitous terms
# UNIGRAM_STOPWORDS: ALL_STOPWORDS + generic English — for distinctive-term extraction
ALL_STOPWORDS = STOPWORDS | DOMAIN_STOPWORDS | _PROCEDURAL_STOPWORDS | _COUNTRY_STOPWORDS
BIGRAM_STOPWORDS = STOPWORDS | DOMAIN_STOPWORDS | _COUNTRY_STOPWORDS
UNIGRAM_STOPWORDS = ALL_STOPWORDS | _GENERIC_ENGLISH_STOPWORDS


def count_phrases(text, phrases):
    """Count occurrences of phrases in text using pre-compiled regex patterns."""
    if not isinstance(text, str):
        return 0
    total = 0
    for kw in phrases:
        pattern = _get_compiled_pattern(kw)
        total += len(pattern.findall(text))
    return total


@st.cache_data
def article_frequency(df, article_dict, groupby=None):
    """Article frequency via single-pass multi-pattern matching."""
    # Reverse map: lowercased keyword -> list of article names
    kw_to_articles = {}
    for art, keywords in article_dict.items():
        for kw in keywords:
            kw_to_articles.setdefault(kw.lower(), []).append(art)

    # Combined regex, longest keywords first to prefer full phrases
    all_keywords = sorted(kw_to_articles.keys(), key=len, reverse=True)
    combined = re.compile(
        r"\b(" + "|".join(re.escape(kw) for kw in all_keywords) + r")\b",
        re.IGNORECASE,
    )

    rows = []
    iterable = [(None, df)] if not groupby else df.groupby(groupby)

    for g, sub in iterable:
        article_counts = {art: 0 for art in article_dict}

        for text in sub["clean_text"]:
            if not isinstance(text, str):
                continue
            for m in combined.finditer(text):
                for art in kw_to_articles[m.group().lower()]:
                    article_counts[art] += 1

        for art, count in article_counts.items():
            if count > 0:
                rows.append(
                    {
                        "group": ("All" if g is None else g),
                        "article": art,
                        "count": count,
                    }
                )

    out = pd.DataFrame(rows)
    return out.sort_values("count", ascending=False) if len(out) > 0 else out


@st.cache_data
def keyword_counts(df, top_n=30, remove_stopwords=True, min_word_length=3):
    """
    Extract most frequent meaningful terms from documents.

    Args:
        df: DataFrame with 'clean_text' column
        top_n: Number of top terms to return
        remove_stopwords: Whether to filter out common stopwords
        min_word_length: Minimum word length to consider

    Returns:
        DataFrame with columns ['term', 'freq'] sorted by frequency
    """
    cnt = Counter()

    for text in df["clean_text"].astype(str).tolist():
        # Extract words using regex (handles punctuation better)
        words = re.findall(r"\b[a-z]+\b", text.lower())

        # Filter words
        filtered_words = [
            w
            for w in words
            if len(w) >= min_word_length  # Minimum length
            and (not remove_stopwords or w not in ALL_STOPWORDS)  # Remove stopwords if enabled
            and not w.isdigit()  # Remove pure numbers
        ]

        cnt.update(filtered_words)

    return (
        pd.DataFrame(cnt.items(), columns=["term", "freq"])
        .sort_values("freq", ascending=False)
        .head(top_n)
    )


def extract_distinctive_terms(
    country_df,
    reference_df,
    top_n=10,
):
    """Extract terms that are distinctively over-represented in *country_df*
    compared to the full *reference_df* corpus, using log-ratio keyness.

    Mirrors the keyness approach used by ``extract_ngrams`` for bigrams:
    ``log2((country_rate + ε) / (corpus_rate + ε))``.  Terms are ranked by
    pure over-representation — frequency is only used as a minimum threshold.

    Returns:
        DataFrame with columns ``['term', 'freq', 'keyness']`` sorted by
        keyness descending, or an empty DataFrame if insufficient data.
    """
    from sklearn.feature_extraction.text import CountVectorizer

    texts = country_df["clean_text"].dropna().astype(str).tolist()
    ref_texts = reference_df["clean_text"].dropna().astype(str).tolist()

    if len(texts) < 1 or len(ref_texts) < 5:
        return pd.DataFrame(columns=["term", "freq", "keyness"])

    stop_words = list(UNIGRAM_STOPWORDS)

    # Fit on full corpus so vocabulary & IDF denominator are stable
    corpus_vec = CountVectorizer(
        min_df=3,
        max_df=0.80,
        stop_words=stop_words,
        lowercase=True,
        token_pattern=r"\b[a-zA-Z]{4,}\b",  # 4+ chars — eliminates "set", "pdf", etc.
    )
    corpus_mat = corpus_vec.fit_transform(ref_texts)
    vocab = corpus_vec.get_feature_names_out()
    corpus_freqs = corpus_mat.sum(axis=0).A1.astype(float)
    corpus_total = corpus_freqs.sum()

    # Transform country subset using the same vocabulary
    country_mat = corpus_vec.transform(texts)
    country_freqs = country_mat.sum(axis=0).A1.astype(float)
    country_total = country_freqs.sum()

    if country_total == 0:
        return pd.DataFrame(columns=["term", "freq", "keyness"])

    # Log-ratio keyness
    eps = 1e-8
    country_rate = country_freqs / country_total
    corpus_rate = corpus_freqs / corpus_total
    log_ratio = np.log2((country_rate + eps) / (corpus_rate + eps))

    term_df = pd.DataFrame(
        {
            "term": vocab,
            "freq": country_freqs.astype(int),
            "keyness": np.round(log_ratio, 4),
        }
    )

    # Dynamic min_freq: at least 3 occurrences, or 20% of doc count
    n_docs = len(texts)
    dynamic_min = max(3, n_docs // 5)
    # Keyness > 1.0 → term is at least 2× over-represented vs corpus
    term_df = term_df[(term_df["freq"] >= dynamic_min) & (term_df["keyness"] > 1.0)]
    term_df = term_df.sort_values("keyness", ascending=False).head(top_n)

    return term_df.reset_index(drop=True)


@st.cache_data
def tfidf_by_doc_type(df, top_n=20):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        st.warning("scikit-learn not installed; using frequency fallback.")
        return keyword_counts(df, top_n).assign(doc_type="All").rename(columns={"freq": "score"})
    rows = []
    for dt, sub in df.groupby("doc_type"):
        docs = sub["clean_text"].dropna().astype(str).tolist()
        if len(docs) < 2:
            topk = keyword_counts(sub, top_n)
            topk["doc_type"] = dt
            rows.append(topk.rename(columns={"freq": "score"}))
            continue
        n_docs = len(docs)
        min_df = 1 if n_docs < 10 else 2
        max_df = 1.0 if n_docs <= 3 else 0.9
        try:
            vec = TfidfVectorizer(min_df=min_df, max_df=max_df, ngram_range=(1, 2))
            mat = vec.fit_transform(docs)
            terms = np.array(vec.get_feature_names_out())
            scores = np.asarray(mat.mean(axis=0)).ravel()
            idx = scores.argsort()[::-1][:top_n]
            tmp = pd.DataFrame({"term": terms[idx], "score": scores[idx], "doc_type": dt})
            rows.append(tmp)
        except ValueError:
            topk = keyword_counts(sub, top_n)
            topk["doc_type"] = dt
            rows.append(topk.rename(columns={"freq": "score"}))
    return pd.concat(rows, ignore_index=True)


@st.cache_data
def extract_ngrams(
    df,
    n=2,
    top_n=20,
    min_freq=5,
    remove_stopwords=True,
    reference_df=None,
):
    """
    Extract most frequent n-grams from documents.

    When *reference_df* is supplied the function uses a **keyness** approach:
    bigrams are ranked by how over-represented they are in *df* compared to
    the full corpus (*reference_df*), using a log-ratio score.  This
    automatically suppresses procedural boilerplate, place names, and any
    other noise that appears at a similar rate across the whole corpus —
    no manual stopwords needed for those cases.

    Args:
        df: DataFrame with 'clean_text' column (country subset)
        n: N-gram size (2 for bi-grams, 3 for tri-grams)
        top_n: Number of top n-grams to return
        min_freq: Minimum document frequency
        remove_stopwords: Whether to filter stopwords
        reference_df: Full-corpus DataFrame for keyness comparison.
                      If None, falls back to raw frequency ranking.

    Returns:
        DataFrame with columns ['phrase', 'freq'] (and 'keyness' when
        reference_df is provided)
    """
    from sklearn.feature_extraction.text import CountVectorizer

    # Configure vectorizer — use lighter BIGRAM_STOPWORDS (keyness handles
    # corpus-wide noise); ALL_STOPWORDS is too aggressive for bigrams
    stop_words = list(BIGRAM_STOPWORDS) if remove_stopwords else None
    vect_kwargs = dict(
        ngram_range=(n, n),
        stop_words=stop_words,
        lowercase=True,
        token_pattern=r"\b[a-zA-Z]{3,}\b",  # 3+ char tokens
    )

    texts = df["clean_text"].dropna().astype(str).tolist()
    if len(texts) < max(min_freq, 1):
        return pd.DataFrame(columns=["phrase", "freq"])

    # ------------------------------------------------------------------
    # Keyness mode — compare country vs full corpus
    # ------------------------------------------------------------------
    if reference_df is not None:
        ref_texts = reference_df["clean_text"].dropna().astype(str).tolist()
        if len(ref_texts) < 5:
            # Not enough reference data — fall back to frequency mode
            reference_df = None

    if reference_df is not None:
        ref_texts = reference_df["clean_text"].dropna().astype(str).tolist()

        # Fit on the full corpus so vocabulary is consistent
        corpus_vec = CountVectorizer(min_df=3, max_df=0.8, **vect_kwargs)
        corpus_mat = corpus_vec.fit_transform(ref_texts)
        vocab = corpus_vec.get_feature_names_out()
        corpus_freqs = corpus_mat.sum(axis=0).A1.astype(float)
        corpus_total = corpus_freqs.sum()

        # Transform the country subset using the same vocabulary
        country_mat = corpus_vec.transform(texts)
        country_freqs = country_mat.sum(axis=0).A1.astype(float)
        country_total = country_freqs.sum()

        if country_total == 0:
            return pd.DataFrame(columns=["phrase", "freq"])

        # Pure log-ratio keyness: log2( (country_rate + ε) / (corpus_rate + ε) )
        # Ranking is by over-representation alone — frequency is only used
        # as a minimum threshold, not as a weight.  This prevents high-freq
        # generic CRPD bigrams from drowning out genuinely distinctive terms.
        eps = 1e-8
        country_rate = country_freqs / country_total
        corpus_rate = corpus_freqs / corpus_total
        log_ratio = np.log2((country_rate + eps) / (corpus_rate + eps))

        ngram_df = pd.DataFrame(
            {
                "phrase": vocab,
                "freq": country_freqs.astype(int),
                "keyness": np.round(log_ratio, 4),
            }
        )

        # Dynamic min_freq: at least 3 occurrences, or 20% of the
        # country's doc count — whichever is higher.  Eliminates
        # proper-name flukes in small corpora.
        n_docs = len(texts)
        dynamic_min = max(3, n_docs // 5)
        # Keyness > 1.0 means the bigram is at least 2× as frequent
        # in the country as in the full corpus.
        ngram_df = ngram_df[(ngram_df["freq"] >= dynamic_min) & (ngram_df["keyness"] > 1.0)]
        ngram_df = ngram_df.sort_values("keyness", ascending=False)

    else:
        # ------------------------------------------------------------------
        # Fallback: raw frequency mode (original behaviour)
        # ------------------------------------------------------------------
        vectorizer = CountVectorizer(min_df=min_freq, max_df=0.8, **vect_kwargs)

        if len(texts) < min_freq:
            return pd.DataFrame(columns=["phrase", "freq"])

        X = vectorizer.fit_transform(texts)
        phrases = vectorizer.get_feature_names_out()
        freqs = X.sum(axis=0).A1

        ngram_df = pd.DataFrame({"phrase": phrases, "freq": freqs.astype(int)}).sort_values(
            "freq", ascending=False
        )

    # ------------------------------------------------------------------
    # Post-filter for bigrams
    # ------------------------------------------------------------------
    if n == 2 and len(ngram_df) > 0:
        parts_df = ngram_df["phrase"].str.split(expand=True)
        if parts_df.shape[1] == 2:
            # Remove duplicate-word bigrams ("sfs sfs")
            ngram_df = ngram_df[parts_df[0].values != parts_df[1].values]

            # Deduplicate reversed bigrams ("ibid arts" / "arts ibid"):
            # canonicalize each pair by alphabetical sort, keep the higher-ranked one
            parts_df = ngram_df["phrase"].str.split(expand=True)
            if len(parts_df) > 0 and parts_df.shape[1] == 2:
                canonical = parts_df.apply(lambda r: " ".join(sorted([r[0], r[1]])), axis=1)
                ngram_df = ngram_df.assign(_canon=canonical.values)
                ngram_df = ngram_df.drop_duplicates(subset="_canon", keep="first")
                ngram_df = ngram_df.drop(columns="_canon")

    return ngram_df[["phrase", "freq"]].head(top_n)


@st.cache_data
def extract_topics_lda(df, n_topics=5, n_words=10, remove_stopwords=True):
    """
    Extract topics using Latent Dirichlet Allocation (LDA).

    Args:
        df: DataFrame with 'clean_text' column
        n_topics: Number of topics to extract
        n_words: Number of top words per topic
        remove_stopwords: Whether to filter stopwords

    Returns:
        Dictionary with topics, labels, and document-topic distribution
    """
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.feature_extraction.text import CountVectorizer

    texts = df["clean_text"].dropna().astype(str).tolist()
    if len(texts) < n_topics:
        # Not enough documents to extract the requested number of topics
        return None

    # Configure vectorizer
    stop_words = list(ALL_STOPWORDS) if remove_stopwords else None
    # Use a dynamic min_df to avoid empty vocabularies on small datasets
    min_df_dynamic = 1 if len(texts) < 5 else 5
    vectorizer = CountVectorizer(
        stop_words=stop_words,
        min_df=min_df_dynamic,  # Ignore terms in <min_df_dynamic documents
        max_df=0.7,  # Ignore terms in >70% of documents
        lowercase=True,
        max_features=1000,  # Limit vocabulary size
        token_pattern=r"\b[a-zA-Z]{3,}\b",  # Min 3 chars, letters only
    )

    # Create document-term matrix
    try:
        X = vectorizer.fit_transform(texts)
    except ValueError:
        # This typically indicates an empty vocabulary (e.g., after stopword removal)
        return None

    # Apply LDA
    lda = LatentDirichletAllocation(
        n_components=n_topics, random_state=42, max_iter=20, learning_method="online"
    )
    doc_topic_dist = lda.fit_transform(X)

    # Extract top words per topic
    feature_names = vectorizer.get_feature_names_out()
    topics = []
    for topic_idx, topic in enumerate(lda.components_):
        top_indices = topic.argsort()[-n_words:][::-1]
        top_words = [feature_names[i] for i in top_indices]
        top_weights = [float(topic[i]) for i in top_indices]
        topics.append({"topic_id": topic_idx, "words": top_words, "weights": top_weights})

    # Generate topic labels (top 5 words for better interpretability)
    topic_labels = [f"Topic {i + 1}: {', '.join(t['words'][:5])}" for i, t in enumerate(topics)]

    # Calculate topic prevalence (% of documents where topic is dominant)
    dominant_topics = doc_topic_dist.argmax(axis=1)
    topic_prevalence = [
        (dominant_topics == i).sum() / len(dominant_topics) * 100 for i in range(n_topics)
    ]

    return {
        "topics": topics,
        "topic_labels": topic_labels,
        "topic_prevalence": topic_prevalence,
        "doc_topic_dist": doc_topic_dist,
        "feature_names": feature_names,
    }


_STOPWORD_VERSION = len(ALL_STOPWORDS)  # cache-bust when stopwords change


def _preprocess_for_topics(text):
    """Strip UN document artifacts before topic modeling.

    Removes document reference codes, paragraph/article cross-references,
    standalone numbers, and very short tokens that produce noise topics.
    """
    # Remove UN document reference codes (CRPD/C/XXX/1, A/HRC/46/27, etc.)
    text = re.sub(r"\b[A-Z]{1,5}/[A-Z0-9/.]+\b", " ", text)
    # Remove paragraph references (para. 14, paras. 23-45)
    text = re.sub(r"\bparas?\.?\s*\d[\d\s,\-\u2013]*", " ", text, flags=re.IGNORECASE)
    # Remove article cross-references (article 5 (3), articles 1-4)
    text = re.sub(r"\barticles?\s*\d[\d\s,\-\u2013()]*", " ", text, flags=re.IGNORECASE)
    # Remove standalone numbers and number-letter combos
    text = re.sub(r"\b\d+[a-z]?\b", " ", text)
    # Strip LOI formulaic question patterns
    text = re.sub(
        r"please\s+(specify|clarify|provide|explain|indicate|describe|elaborate|inform)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    # Strip committee formulaic patterns
    text = re.sub(
        r"the\s+committee\s+(commends|regrets|notes|welcomes|recommends|appreciates"
        r"|encourages|reiterates|recalls|invites|urges|requests)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    # Strip "in response to question/paragraph" patterns
    text = re.sub(
        r"in\s+response\s+to\s+(the\s+)?(question|list|issues?|paragraph|request)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    # Remove single and two-character tokens
    text = re.sub(r"\b[a-zA-Z]{1,2}\b", " ", text)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


@st.cache_resource
def _fit_global_topics(texts_tuple, n_topics=7, _sw_version=_STOPWORD_VERSION):
    """Fit NMF on TF-IDF for the *full* corpus once and cache the model.

    NMF on TF-IDF produces sparser, more interpretable topics than LDA
    for domain-specific corpora like CRPD reports.  The IDF component
    naturally downweights corpus-wide generic terms.  Texts are
    preprocessed to remove UN document artifacts before vectorization.

    Returns (nmf_model, vectorizer, topic_labels, feature_names).
    """
    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfVectorizer

    texts = [_preprocess_for_topics(t) for t in texts_tuple]
    stop_words = list(ALL_STOPWORDS)
    vectorizer = TfidfVectorizer(
        stop_words=stop_words,
        min_df=15,
        max_df=0.35,
        lowercase=True,
        max_features=2000,
        token_pattern=r"\b[a-zA-Z]{4,}\b",
    )
    X = vectorizer.fit_transform(texts)
    nmf = NMF(
        n_components=n_topics,
        init="nndsvda",
        random_state=42,
        max_iter=300,
    )
    nmf.fit(X)

    feature_names = vectorizer.get_feature_names_out()
    topic_labels = []
    for i, component in enumerate(nmf.components_):
        top_words = [feature_names[j] for j in component.argsort()[-5:][::-1]]
        topic_labels.append(f"Topic {i + 1}: {', '.join(top_words)}")

    return nmf, vectorizer, topic_labels, feature_names


def global_topic_transform(full_df, subset_df, n_topics=7):
    """Project *subset_df* documents onto topics learned from *full_df*.

    Because the NMF model is fitted on the entire corpus, topics are
    stable regardless of which countries are selected.

    Returns the same dict shape as ``extract_topics_lda`` or ``None``.
    """
    full_texts = full_df["clean_text"].dropna().astype(str).tolist()
    if len(full_texts) < n_topics:
        return None

    try:
        nmf, vectorizer, topic_labels, feature_names = _fit_global_topics(
            tuple(full_texts), n_topics=n_topics
        )
    except ValueError:
        return None

    # Transform the *subset* documents using the already-fitted vectorizer + NMF
    subset_texts = subset_df["clean_text"].dropna().astype(str).tolist()
    if not subset_texts:
        return None

    try:
        X_sub = vectorizer.transform(subset_texts)
    except ValueError:
        return None

    doc_topic_dist = nmf.transform(X_sub)
    # Normalize rows to sum to 1 for interpretable proportions
    row_sums = doc_topic_dist.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # avoid division by zero
    doc_topic_dist = doc_topic_dist / row_sums

    # Build per-topic info
    topics = []
    for topic_idx, component in enumerate(nmf.components_):
        top_indices = component.argsort()[-10:][::-1]
        top_words = [feature_names[j] for j in top_indices]
        top_weights = [float(component[j]) for j in top_indices]
        topics.append({"topic_id": topic_idx, "words": top_words, "weights": top_weights})

    dominant = doc_topic_dist.argmax(axis=1)
    prevalence = [(dominant == i).sum() / len(dominant) * 100 for i in range(n_topics)]

    return {
        "topics": topics,
        "topic_labels": topic_labels,
        "topic_prevalence": prevalence,
        "doc_topic_dist": doc_topic_dist,
        "feature_names": feature_names,
    }


@st.cache_data
def model_shift_table(df):
    rows = []
    for _, r in df.iterrows():
        text = str(r.get("clean_text", ""))
        counts = {m: count_phrases(text, kws) for m, kws in MODEL_DICT.items()}
        total = sum(counts.values()) if sum(counts.values()) > 0 else 1
        rows.append(
            {
                "country": r.get("country", "Unknown"),
                "region": r.get("region", "Unknown"),
                "year": r.get("year", np.nan),
                "medical": counts["Medical Model"],
                "rights": counts["Rights-Based Model"],
                "rights_share": counts["Rights-Based Model"] / total,
            }
        )
    return pd.DataFrame(rows)


def generate_smart_insights(
    df, yearly_model_df=None, region_counts_df=None, yearly_counts_df=None, bump_df=None
):
    """Generate dynamic insights tied to visible homepage charts.

    Returns a list of dicts: [{"label": str, "text": str}, ...]
    Each insight directly interprets data from a specific chart on the page.
    """
    insights = []

    # 1. Submissions Trend — reads from bar chart (yearly_counts_df)
    if yearly_counts_df is not None and len(yearly_counts_df) >= 2:
        n_total = int(yearly_counts_df["count"].sum())
        peak_row = yearly_counts_df.loc[yearly_counts_df["count"].idxmax()]
        peak_year = int(peak_row["year"])
        peak_count = int(peak_row["count"])
        latest_year = int(yearly_counts_df["year"].max())
        # Detect recent trend (last 3 years)
        recent = yearly_counts_df[yearly_counts_df["year"] >= latest_year - 2].sort_values("year")
        if len(recent) >= 2:
            first_recent = int(recent["count"].iloc[0])
            last_recent = int(recent["count"].iloc[-1])
            pct_change = (
                abs(last_recent - first_recent) / first_recent * 100 if first_recent > 0 else 0
            )
            if last_recent > first_recent and pct_change >= 10:
                direction = "an upward trend"
            elif last_recent < first_recent and pct_change >= 10:
                direction = "a declining trend"
            else:
                direction = "a stable pattern"
        else:
            direction = None

        text = (
            f"Submissions peaked in {peak_year} with {peak_count} documents "
            f"(out of {n_total} total)."
        )
        if direction and peak_year != latest_year:
            text += f" Recent years show {direction}."
        text += " Submission counts reflect UN processing timelines, not just State Party effort."
        insights.append({"label": "Submissions Trend", "text": text})

    # 2. Model Shift — reads from stacked area chart (yearly_model_df)
    if yearly_model_df is not None and len(yearly_model_df) >= 2:
        first_row = yearly_model_df.iloc[0]
        last_row = yearly_model_df.iloc[-1]
        first_rights = first_row["Rights-Based"]
        last_rights = last_row["Rights-Based"]
        shift = last_rights - first_rights
        first_yr = int(first_row["year"])
        last_yr = int(last_row["year"])
        n_years = len(yearly_model_df)

        if abs(shift) >= 1:
            direction = "grew" if shift > 0 else "declined"
            text = (
                f"Based on keyword matching across {n_years} reporting years, "
                f"rights-based language {direction} from {first_rights:.0f}% to "
                f"{last_rights:.0f}% since {first_yr} — a {abs(shift):.0f} percentage-point "
                f"shift."
            )
        else:
            text = (
                f"Based on keyword matching across {n_years} reporting years, "
                f"rights-based language has held steady at ~{last_rights:.0f}% "
                f"across {first_yr}–{last_yr}."
            )
        insights.append({"label": "Keyword Shift", "text": text})

    # 3. Regional Gap — reads from lollipop chart (region_counts_df)
    # Uses docs-per-State-Party (normalized) to match the lollipop chart
    if region_counts_df is not None and len(region_counts_df) >= 2:
        if "docs_per_sp" in region_counts_df.columns:
            # Already normalized — use directly
            top = region_counts_df.iloc[-1]
            bottom = region_counts_df.iloc[0]
            n_regions = len(region_counts_df)
            ratio = top["docs_per_sp"] / bottom["docs_per_sp"] if bottom["docs_per_sp"] > 0 else 0
            text = (
                f"{top['region']} leads with {top['docs_per_sp']:.1f} documents per "
                f"State Party — {ratio:.1f}\u00d7 the rate of {bottom['region']} "
                f"({bottom['docs_per_sp']:.1f}). "
                f"Differences in regional reporting rates may relate to ratification "
                f"dates and institutional capacity, but other factors are not captured "
                f"in this data ({n_regions} regions)."
            )
        else:
            # Compute normalized values inline from raw counts + df
            _n_countries_per = {}
            if df is not None and "region" in df.columns and "country" in df.columns:
                _n_countries_per = df.groupby("region")["country"].nunique().to_dict()
            _rc = region_counts_df.copy()
            _rc["n_countries"] = _rc["region"].map(_n_countries_per).fillna(1)
            _rc["docs_per_sp"] = (_rc["documents"] / _rc["n_countries"]).round(1)
            _rc = _rc.sort_values("docs_per_sp", ascending=True)
            top = _rc.iloc[-1]
            bottom = _rc.iloc[0]
            n_regions = len(_rc)
            ratio = top["docs_per_sp"] / bottom["docs_per_sp"] if bottom["docs_per_sp"] > 0 else 0
            text = (
                f"{top['region']} leads with {top['docs_per_sp']:.1f} documents per "
                f"State Party — {ratio:.1f}\u00d7 the rate of {bottom['region']} "
                f"({bottom['docs_per_sp']:.1f}). "
                f"Differences in regional reporting rates may relate to ratification "
                f"dates and institutional capacity, but other factors are not captured "
                f"in this data ({n_regions} regions)."
            )
        insights.append({"label": "Regional Gap", "text": text})

    # 4. Reporting Gaps — countries with no document in 3+ years
    if df is not None and len(df) and "country" in df.columns and "year" in df.columns:
        ref_year = int(df["year"].max())
        latest_per_country = df.groupby("country")["year"].max()
        gap_count = int((ref_year - latest_per_country >= 3).sum())
        if gap_count > 0:
            text = (
                f"{gap_count} States Parties have not submitted any document in "
                f"3+ years. This may reflect processing delays or reporting gaps "
                f"requiring follow-up."
            )
            insights.append({"label": "Reporting Gaps", "text": text})

    # 5. Reporting Cycles — States Parties with at least one complete cycle
    if df is not None and len(df) and "country" in df.columns and "doc_type" in df.columns:
        cycle_types = {"State Report", "Concluding Observations"}
        country_types = df.groupby("country")["doc_type"].apply(set)
        n_complete = int(country_types.apply(lambda s: cycle_types.issubset(s)).sum())
        n_total_countries = int(country_types.shape[0])
        pct = round(n_complete / n_total_countries * 100) if n_total_countries > 0 else 0
        text = (
            f"Only {n_complete} of {n_total_countries} States Parties ({pct}%) "
            f"have completed at least one full reporting cycle "
            f"(State Report through Concluding Observations)."
        )
        insights.append({"label": "Reporting Cycles", "text": text})

    return insights
