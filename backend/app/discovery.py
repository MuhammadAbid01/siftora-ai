"""Turning raw search results into real company lead candidates.

A web search result is a *source* — a page on which a company may be
mentioned — never a lead in its own right. Before this module existed, the
research graph took each search result and used its page title as the
company name and its URL's domain as the company domain, so a query like
"20 best animation agencies in Dubai" created leads named
"Top 15+ Animation Studios In Dubai (2026)" (a listicle on `edvido.com`) or
"What are the top-rated animation studios in the UAE? - Quora", instead of
the companies those pages list.

This module supplies the deterministic half of the fix:

* `is_non_company_domain` — reference/encyclopedic/directory/social/news
  hosts that are never themselves the company we're prospecting for. Such
  a page can still be *mined* for the companies it mentions, and can be
  cited as evidence, but it can never become a lead.
* `looks_like_listing_page` — a cheap pre-classification hint (listicle /
  roundup / directory) used to steer the entity-extraction prompt.
* `is_valid_company_name` / `clean_company_name` — a conservative gate that
  rejects names that are obviously page titles, questions, domains or
  generic navigation labels rather than businesses.

The probabilistic half (reading a page and naming the companies on it)
lives in `LanguageModelProvider.extract_companies_from_page`.
"""

import re
from urllib.parse import urlparse

# --- Non-company domains -------------------------------------------------
#
# Matched as suffixes against the normalized (scheme-less, `www.`-less)
# domain, so `en.wikipedia.org` matches `wikipedia.org` and
# `clutch.co/ae/...`'s host matches `clutch.co`. This is a denylist of
# *hosts*, not of content: a listicle published on an ordinary company's
# own blog (e.g. `austinvisuals.com/animation-studios-in-dubai`) is caught
# by `looks_like_listing_page` instead, which is why both checks exist.

_REFERENCE_DOMAINS = frozenset(
    {
        "wikipedia.org",
        "wikimedia.org",
        "wikidata.org",
        "wiktionary.org",
        "wikivoyage.org",
        "fandom.com",
        "britannica.com",
        "investopedia.com",
        "dbpedia.org",
        "gem.wiki",
        "sourcewatch.org",
        "everipedia.org",
        "scholar.google.com",
        "archive.org",
    }
)

# Directory / aggregator / marketplace / review sites. These list or rank
# other businesses; their own domain is never the prospect.
_DIRECTORY_DOMAINS = frozenset(
    {
        "clutch.co",
        "sortlist.com",
        "sortlist.co.uk",
        "themanifest.com",
        "goodfirms.co",
        "designrush.com",
        "techbehemoths.com",
        "expertise.com",
        "superbcompanies.com",
        "edvido.com",
        "agencyspotter.com",
        "topdevelopers.co",
        "selectedfirms.co",
        "businessofapps.com",
        "crunchbase.com",
        "pitchbook.com",
        "owler.com",
        "zoominfo.com",
        "dnb.com",
        "bloomberg.com",
        # Startup/company databases. Their profile pages look like company
        # pages and link internally, so without this they become the "lead".
        "tracxn.com",
        "cbinsights.com",
        "dealroom.co",
        "f6s.com",
        "wellfound.com",
        "angel.co",
        "angellist.com",
        "startupranking.com",
        "growjo.com",
        "apollo.io",
        "lusha.com",
        "rocketreach.co",
        "signalhire.com",
        "leadiq.com",
        "opencorporates.com",
        "companieshouse.gov.uk",
        "bizapedia.com",
        "manta.com",
        "kompass.com",
        "europages.co.uk",
        "europages.com",
        "alibaba.com",
        "indiamart.com",
        "tradeindia.com",
        # Financial data / market-quote sites. A stock index page (e.g.
        # investing.com's Karachi-30 components) otherwise turns every
        # listed constituent into a lead domained to the quote site.
        "investing.com",
        "tradingview.com",
        "marketwatch.com",
        "finance.yahoo.com",
        "yahoo.com",
        "morningstar.com",
        "moneycontrol.com",
        "stockanalysis.com",
        "wsj.com",
        "ft.com",
        "nasdaq.com",
        "nyse.com",
        "psx.com.pk",
        "investopedia.com",
        "simplywall.st",
        "gurufocus.com",
        "macrotrends.net",
        "wisesheets.io",
        "yelp.com",
        "yellowpages.com",
        "yell.com",
        "trustpilot.com",
        "g2.com",
        "capterra.com",
        "getapp.com",
        "softwareadvice.com",
        "producthunt.com",
        "glassdoor.com",
        "indeed.com",
        "ziprecruiter.com",
        "upwork.com",
        "fiverr.com",
        "freelancer.com",
        "tripadvisor.com",
        "foursquare.com",
        "justdial.com",
        "yellowpages.ae",
        "connect.ae",
        "uaecontact.com",
        "dubaibusinessdirectory.com",
    }
)

_SOCIAL_DOMAINS = frozenset(
    {
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "youtube.com",
        "youtu.be",
        "tiktok.com",
        "pinterest.com",
        "reddit.com",
        "quora.com",
        "threads.net",
        "snapchat.com",
        "vimeo.com",
        "behance.net",
        "dribbble.com",
        "github.com",
        "gitlab.com",
        "stackoverflow.com",
        "discord.com",
        "telegram.org",
        "whatsapp.com",
    }
)

# Free publishing hosts — the host belongs to the platform, not to whoever
# writes there, so the domain can never identify a company.
_PUBLISHING_DOMAINS = frozenset(
    {
        "medium.com",
        "substack.com",
        "blogspot.com",
        "wordpress.com",
        "tumblr.com",
        "wixsite.com",
        "weebly.com",
        "blogger.com",
        "notion.site",
        "sites.google.com",
        "docs.google.com",
        "drive.google.com",
        "issuu.com",
        "slideshare.net",
        "scribd.com",
        "wetransfer.com",
        "behance.net",
        "carrd.co",
        "linktr.ee",
    }
)

_NEWS_DOMAINS = frozenset(
    {
        "nytimes.com",
        "wsj.com",
        "bbc.com",
        "bbc.co.uk",
        "cnn.com",
        "reuters.com",
        "apnews.com",
        "theguardian.com",
        "forbes.com",
        "fortune.com",
        "businessinsider.com",
        "entrepreneur.com",
        "inc.com",
        "techcrunch.com",
        "wired.com",
        "theverge.com",
        "venturebeat.com",
        "mashable.com",
        "gulfnews.com",
        "khaleejtimes.com",
        "thenationalnews.com",
        "arabianbusiness.com",
        "zawya.com",
        "timeoutdubai.com",
        "hespress.com",
    }
)

_SEARCH_ENGINE_DOMAINS = frozenset(
    {
        "google.com",
        "bing.com",
        "duckduckgo.com",
        "yahoo.com",
        "baidu.com",
        "yandex.com",
    }
)

NON_COMPANY_DOMAINS: frozenset[str] = frozenset(
    _REFERENCE_DOMAINS
    | _DIRECTORY_DOMAINS
    | _SOCIAL_DOMAINS
    | _PUBLISHING_DOMAINS
    | _NEWS_DOMAINS
    | _SEARCH_ENGINE_DOMAINS
)

# Government, military and academic hosts are institutions, not prospects.
# Matched as a *label*, not a suffix: enumerating suffixes missed
# `karachi.mfa.gov.sg` (a consulate), which became a lead in a live run
# because the list happened to contain `.gov.uk` and `.gov.ae` but not
# `.gov.sg`. Every country spells this differently, so check the last few
# labels for the institutional marker instead of guessing at the list.
_INSTITUTIONAL_LABELS = frozenset({"gov", "gouv", "gob", "govt", "mil", "edu", "ac"})

# Hosts that are not worth fetching at all. They sit behind a login or
# render nothing useful to a scraper, so every fetch is a guaranteed-wasted
# extraction call — observed live: a Facebook group and a Scribd document
# were both fetched, both returned no content, and both were then skipped.
# Mining still happens for ordinary directories (Clutch, Tracxn); this is
# only for hosts that reliably yield nothing.
NEVER_FETCH_DOMAINS: frozenset[str] = frozenset(
    {
        "facebook.com",
        "instagram.com",
        "linkedin.com",
        "twitter.com",
        "x.com",
        "tiktok.com",
        "pinterest.com",
        "snapchat.com",
        "threads.net",
        "youtube.com",
        "youtu.be",
        "vimeo.com",
        "scribd.com",
        "issuu.com",
        "slideshare.net",
        "docs.google.com",
        "drive.google.com",
        "whatsapp.com",
        "telegram.org",
        "discord.com",
    }
)


def should_never_fetch(domain: str) -> bool:
    """True for login-walled or non-scrapable hosts — skip before paying for extraction."""
    return _host_matches(domain, NEVER_FETCH_DOMAINS)


def _host_matches(domain: str, candidates: frozenset[str]) -> bool:
    """True when `domain` is one of `candidates` or a subdomain of one."""
    domain = domain.strip().lower().rstrip(".")
    return any(domain == c or domain.endswith("." + c) for c in candidates)


# Country/language front-ends for the same publisher: `uk.investing.com` and
# `investing.com` are one site, and must not look like two companies.
_GENERIC_SUBDOMAINS = frozenset(
    {
        "www",
        "m",
        "en",
        "uk",
        "us",
        "ca",
        "au",
        "in",
        "de",
        "fr",
        "es",
        "it",
        "nl",
        "pt",
        "br",
        "ae",
        "pk",
        "sg",
        "jp",
        "cn",
        "ru",
        "tr",
        "pl",
        "za",
        "mx",
        "ar",
        "blog",
        "news",
        "shop",
        "store",
        "app",
        "web",
        "mobile",
        "beta",
        "staging",
    }
)


def _site_key(domain: str) -> str:
    """Strip leading generic/country subdomains so front-ends of one site collapse together."""
    labels = domain.strip().lower().rstrip(".").split(".")
    while len(labels) > 2 and labels[0] in _GENERIC_SUBDOMAINS:
        labels = labels[1:]
    return ".".join(labels)


def same_site(a: str, b: str) -> bool:
    """True when two hostnames belong to the same website.

    Used to enforce an invariant that no denylist can cover: a company
    listed on an aggregator can never have that aggregator as its own
    website. Directory pages link to internal profile pages
    (`investing.com/equities/attock-refiner`), and taking those at face
    value produced leads whose "company domain" was the directory —
    the exact failure this module exists to prevent — and duplicated a
    company once per country front-end (`investing.com` + `uk.investing.com`).
    """
    if not a or not b:
        return False
    a, b = _site_key(a), _site_key(b)
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def is_reference_domain(domain: str) -> bool:
    """Encyclopedic/reference hosts specifically (Wikipedia and friends).

    Kept separate from the broader denylist because these pages are often
    genuinely *about* one specific company and therefore make good evidence
    sources even though they can never be the lead itself.
    """
    return _host_matches(domain, _REFERENCE_DOMAINS)


def is_non_company_domain(domain: str) -> bool:
    """True when this host is a reference, directory, social, publishing,
    news, search or institutional site — i.e. never the business we are
    prospecting for. Such a page may still be mined for the companies it
    mentions and cited as evidence, but must never become a lead.
    """
    domain = domain.strip().lower().rstrip(".")
    if not domain:
        return True
    # `gov`/`edu`/`mil`/`ac` as one of the trailing labels covers every
    # national spelling (.gov, .gov.sg, .gouv.fr, .ac.uk, .edu.au) without
    # trying to enumerate them.
    if any(label in _INSTITUTIONAL_LABELS for label in domain.split(".")[-3:-1] or []):
        return True
    if domain.split(".")[-1] in _INSTITUTIONAL_LABELS:
        return True
    return _host_matches(domain, NON_COMPANY_DOMAINS)


# --- Listing / listicle detection ---------------------------------------

_LISTICLE_PATTERNS = (
    # "Top 10 ...", "Best 15 ...", "20 best ...", "15+ agencies ..."
    r"\b(?:top|best|leading|greatest)\s+\d+\b",
    r"\b\d+\+?\s+(?:of\s+the\s+)?(?:top|best|leading|greatest|great|amazing)\b",
    r"\b\d+\+?\s+(?:animation|design|marketing|software|creative|digital|video)?\s*"
    r"(?:agencies|companies|studios|firms|startups|brands|vendors|providers)\b",
    # "... companies to watch", "... agencies you should know"
    r"\b(?:agencies|companies|studios|firms|brands)\s+(?:to\s+watch|you\s+should\s+know)\b",
    # Roundup / directory furniture
    r"\blist\s+of\s+\w+",
    r"\b(?:rankings?|directory|listings?|roundup)\b",
    r"\b(?:reviews?|ratings?)\s*(?:&|and)?\s*(?:rankings?)?\s*(?:\||-|–|—|$)",
    r"\bcompare\b|\bcomparison\b",
    r"\b(?:ultimate|complete|definitive)\s+(?:guide|list)\b",
    # "Top X in Y" with no number, e.g. "Top Animation Studios in Dubai".
    # Singular forms matter too: an SEO title segment like "Top Video
    # Production Agency UAE" is a marketing headline, not a trading name.
    r"\b(?:top|best|leading|#\s*1)\s+(?:\w+\s+&?\s*){0,4}"
    r"(?:agency|agencies|company|companies|studio|studios|firm|firms|startups?"
    r"|brands?|vendors?|providers?|services?)\b",
)

_LISTICLE_RE = re.compile("|".join(_LISTICLE_PATTERNS), re.IGNORECASE)

_LISTING_URL_HINTS = (
    "/best-",
    "/top-",
    "-best-",
    "-top-",
    "/rankings",
    "/directory",
    "/listings",
    "/agencies/",
    "/companies/",
    "/reviews/",
    "/blog/",
)


def looks_like_listing_page(*, title: str, url: str = "", snippet: str = "") -> bool:
    """Heuristic "this page probably lists several companies" hint.

    This is deliberately *only a hint*: it steers the entity-extraction
    prompt and is never used on its own to reject a candidate. Plenty of
    real companies publish SEO titles that trip these patterns — e.g.
    "Best 2D & 3D Animation Company in Dubai | Top Video Production Agency
    UAE" is `villagetalkies.ae`'s own homepage. The language model makes
    the final company-site-vs-listing call after reading the page; a false
    positive here only means the page is read with listing-aware framing.
    """
    if _LISTICLE_RE.search(title or ""):
        return True
    if _LISTICLE_RE.search(snippet or ""):
        return True
    path = (urlparse(url).path or "").lower() if url else ""
    return any(hint in path for hint in _LISTING_URL_HINTS)


# --- Company-name validation --------------------------------------------

# Generic page furniture that is a navigation label, not a business.
_GENERIC_NAMES = frozenset(
    {
        "home",
        "homepage",
        "about",
        "about us",
        "contact",
        "contact us",
        "services",
        "our services",
        "portfolio",
        "our work",
        "work",
        "blog",
        "news",
        "careers",
        "jobs",
        "team",
        "our team",
        "clients",
        "pricing",
        "faq",
        "privacy policy",
        "terms of service",
        "untitled",
        "untitled document",
        "page not found",
        "404",
        "404 not found",
        "access denied",
        "just a moment",
        "loading",
        "error",
        "n/a",
        "none",
        "unknown",
        "company",
        "companies",
        "agency",
        "agencies",
        "studio",
        "studios",
        "the company",
    }
)

# The publisher brand that an SEO title trails after the real subject
# ("... - Quora", "... | LinkedIn"). These are never the prospect, and a
# title-derived name must never collapse to one of them.
_PLATFORM_BRANDS = frozenset(
    {
        "wikipedia",
        "wikimedia",
        "quora",
        "reddit",
        "medium",
        "substack",
        "linkedin",
        "facebook",
        "instagram",
        "twitter",
        "x",
        "youtube",
        "tiktok",
        "pinterest",
        "clutch",
        "clutch.co",
        "sortlist",
        "the manifest",
        "goodfirms",
        "designrush",
        "glassdoor",
        "indeed",
        "crunchbase",
        "yelp",
        "trustpilot",
        "g2",
        "capterra",
        "upwork",
        "fiverr",
        "forbes",
        "bloomberg",
        "techcrunch",
        "business insider",
        "entrepreneur",
        "behance",
        "dribbble",
        "github",
        "tripadvisor",
        "britannica",
    }
)

_DOMAIN_LIKE_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?[\w-]+(?:\.[\w-]+)+(?:/\S*)?$",
    re.IGNORECASE,
)

# A leading article number ("10 Best ...") or a trailing year/edition marker
# ("... (2026)", "... - 2026 Reviews") is a dead giveaway for a page title.
_TITLE_ARTIFACT_RE = re.compile(
    r"^\s*\d+[\.\)]?\s+\w|\(\s*(?:19|20)\d{2}\s*\)|\b(?:19|20)\d{2}\s+"
    r"(?:reviews?|rankings?|update|edition|guide)\b",
    re.IGNORECASE,
)

MAX_COMPANY_NAME_WORDS = 8
MAX_COMPANY_NAME_CHARS = 80


# Lowercase words that appear legitimately inside real trading names
# ("Bank of America", "Ben and Jerry's", "Victoria and Albert Museum").
_NAME_CONNECTORS = frozenset(
    {"of", "and", "the", "for", "at", "in", "on", "de", "la", "le", "du", "van", "von", "&", "-"}
)


# Words that carry no identifying signal when matching a name to a domain.
_UNINFORMATIVE_NAME_WORDS = frozenset(
    {
        "the",
        "and",
        "of",
        "company",
        "companies",
        "corporation",
        "corp",
        "group",
        "holdings",
        "holding",
        "limited",
        "ltd",
        "llc",
        "llp",
        "inc",
        "plc",
        "pvt",
        "private",
        "international",
        "global",
        "services",
        "service",
        "solutions",
        "systems",
        "technologies",
        "technology",
        "industries",
        "enterprises",
        "ventures",
        "partners",
        "associates",
        "consulting",
        "studio",
        "studios",
        "agency",
        "agencies",
    }
)


def _name_tokens(name: str) -> list[str]:
    return [w for w in re.sub(r"[^a-z0-9]+", " ", name.lower()).split() if w]


def domain_matches_company(name: str, domain: str, title: str = "") -> bool:
    """Sanity-check that a resolved domain really belongs to `name`.

    Resolving a company's site by searching "<name> official website" and
    taking the first non-denylisted hit is not safe on its own: a live run
    filed "Fauji Fertilizer Company" under `website.com` and "Attock
    Refinery" under `canva.com`, because those were simply the first results
    back. A lead whose domain belongs to someone else is worse than no lead,
    so the match has to be positively evidenced.

    Accepts when a distinctive word of the name appears in the host, when
    the host matches the name's acronym (Fauji Cement Company Limited ->
    `fccl.com.pk`), or when the search result's title contains the name.
    """
    if not name or not domain:
        return False

    host = _site_key(domain).rsplit(".", 1)[0] if "." in domain else domain
    host_letters = re.sub(r"[^a-z0-9]+", "", host.lower())
    if not host_letters:
        return False

    tokens = _name_tokens(name)
    distinctive = [t for t in tokens if t not in _UNINFORMATIVE_NAME_WORDS and len(t) >= 4]

    # A distinctive word of the name appears in the host.
    if any(t in host_letters for t in distinctive):
        return True

    # Acronym match, e.g. "Fauji Cement Company Limited" -> fccl. Needs at
    # least 3 letters, or it would match almost anything.
    acronym = "".join(t[0] for t in tokens if t)
    return len(acronym) >= 3 and host_letters.startswith(acronym)


def page_mentions_company(name: str, page_text: str) -> bool:
    """Does this page actually belong to / talk about this company?

    The decisive check that a resolved domain is the right one. Matching a
    name against a *domain string* is too weak in both directions: it let
    "Fauji Fertilizer Company" resolve to `website.com` and "Fauji Cement
    Company" to `flysfo.com` (San Francisco airport), while rejecting
    `arl.com.pk`, which really is Attock Refinery Limited. The page we fetch
    anyway settles it — a company's own site says its own name.

    Requires the longest distinctive word of the name to appear in the page,
    which tolerates suffix and word-order differences ("Attock Refinery" vs
    "Attock Refinery Limited") without accepting an unrelated site.
    """
    if not name or not page_text:
        return False

    haystack = re.sub(r"[^a-z0-9]+", " ", page_text.lower())
    tokens = [
        t
        for t in _name_tokens(name)
        if t not in _UNINFORMATIVE_NAME_WORDS and len(t) >= 4 and not t.isdigit()
    ]
    if not tokens:
        # Nothing distinctive to look for (e.g. "AB Group") — don't block it
        # here; scoring still has to find real evidence.
        return True

    return any(f" {t} " in f" {haystack} " for t in tokens)


def _looks_like_a_sentence_fragment(words: list[str]) -> bool:
    """True for prose accidentally captured as a name.

    Extraction from long articles sometimes returns a clause rather than an
    entity — e.g. "UAE began to attract South Asian films". Brand names are
    overwhelmingly title-cased or upper-cased; a multi-word candidate that
    is mostly lowercase (ignoring the connectors real names do contain) is
    prose, not a business.
    """
    if len(words) < 4:
        return False

    lowercase_content_words = sum(
        1 for w in words if w[:1].islower() and w.lower().strip(".,'") not in _NAME_CONNECTORS
    )
    return lowercase_content_words / len(words) > 0.4


def is_valid_company_name(name: str | None) -> bool:
    """Conservative gate: reject names that are obviously *not* a business.

    Catches the failure mode this module exists for — listicle titles,
    questions, bare domains and navigation labels being persisted as
    companies — while staying permissive enough not to drop real, oddly
    punctuated business names. When in doubt this returns True; the
    downstream analysis/scoring stages still have to find real evidence
    before such a candidate can qualify.
    """
    if name is None:
        return False

    cleaned = " ".join(name.split())
    if not cleaned:
        return False
    if len(cleaned) < 2 or len(cleaned) > MAX_COMPANY_NAME_CHARS:
        return False
    if cleaned.lower() in _GENERIC_NAMES or cleaned.lower() in _PLATFORM_BRANDS:
        return False
    # A question is a page/thread title ("What are the top-rated animation
    # studios in the UAE?"), never a company name.
    if cleaned.endswith("?") or cleaned.lower().startswith(
        ("what ", "which ", "how ", "why ", "where ", "who ", "when ")
    ):
        return False
    if "@" in cleaned or "://" in cleaned:
        return False
    if _DOMAIN_LIKE_RE.match(cleaned):
        return False
    if _LISTICLE_RE.search(cleaned):
        return False
    if _TITLE_ARTIFACT_RE.search(cleaned):
        return False
    words = cleaned.split()
    # Real company names are short. A long phrase is a headline.
    if len(words) > MAX_COMPANY_NAME_WORDS:
        return False
    if _looks_like_a_sentence_fragment(words):
        return False
    # Needs at least one letter — "2026" or "- -" is not a name.
    return any(ch.isalpha() for ch in cleaned)


_TITLE_SEPARATORS = re.compile(r"\s+[|•·»—–-]\s+|\s*::\s*")

# Boilerplate that SEO titles append to the brand name.
_TITLE_TAIL_NOISE = re.compile(
    r"^(?:home|homepage|official\s+(?:site|website)|welcome|about\s+us)$",
    re.IGNORECASE,
)


def clean_company_name(raw_title: str) -> str | None:
    """Best-effort brand name recovered from an SEO page title.

    "Top Animation Studio In Dubai - Infinity Animations" -> "Infinity
    Animations". Used only as a *fallback* when entity extraction could not
    name the company; the primary path reads the name out of the page
    content. Returns None when no segment survives validation, which the
    caller must treat as "cannot name this company" — never as "use the
    title anyway".
    """
    if not raw_title:
        return None

    segments = [s.strip() for s in _TITLE_SEPARATORS.split(raw_title) if s and s.strip()]
    if not segments:
        return None

    candidates = [s for s in segments if not _TITLE_TAIL_NOISE.match(s)]
    valid = [s for s in candidates if is_valid_company_name(s)]
    if not valid:
        return None

    # Prefer the shortest valid segment: SEO titles pad the descriptive
    # half ("Top Animation Studio In Dubai") and leave the brand bare
    # ("Infinity Animations").
    return min(valid, key=lambda s: (len(s.split()), len(s)))
