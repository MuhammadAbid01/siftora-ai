"""Unit tests for the deterministic lead-candidate gates (app/discovery.py).

These encode the concrete failure mode that motivated the module: a search
for "20 best animation agencies in Dubai" was turning listicles, directory
pages and Wikipedia articles into leads named after their page titles.
"""

import pytest

from app.discovery import (
    clean_company_name,
    domain_matches_company,
    is_non_company_domain,
    is_reference_domain,
    is_valid_company_name,
    looks_like_listing_page,
    page_mentions_company,
    same_site,
    should_never_fetch,
)


class TestNonCompanyDomains:
    @pytest.mark.parametrize(
        "domain",
        [
            "wikipedia.org",
            "en.wikipedia.org",
            "fr.wikipedia.org",
            "britannica.com",
            "clutch.co",
            "sortlist.com",
            "themanifest.com",
            "goodfirms.co",
            "designrush.com",
            "edvido.com",
            "crunchbase.com",
            "glassdoor.com",
            "quora.com",
            "reddit.com",
            "instagram.com",
            "www.instagram.com",
            "linkedin.com",
            "youtube.com",
            "medium.com",
            "someone.blogspot.com",
            "forbes.com",
            "gulfnews.com",
            "khaleejtimes.com",
            "google.com",
            "dubai.gov.ae",
            "mit.edu",
        ],
    )
    def test_known_non_company_hosts_are_rejected(self, domain: str) -> None:
        assert is_non_company_domain(domain) is True

    @pytest.mark.parametrize(
        "domain",
        [
            "northbeamstudio.example",
            "infinityanimations.com",
            "villagetalkies.ae",
            "blinkstudios.ae",
            "captain-studio.com",
            "animationstudio.ae",
        ],
    )
    def test_real_company_hosts_are_allowed(self, domain: str) -> None:
        assert is_non_company_domain(domain) is False

    def test_empty_domain_is_rejected(self) -> None:
        assert is_non_company_domain("") is True

    def test_reference_domains_are_a_narrower_set(self) -> None:
        # Wikipedia is reference *and* non-company; a directory is only the
        # latter, because a reference page about one company is still usable
        # as an evidence source.
        assert is_reference_domain("en.wikipedia.org") is True
        assert is_reference_domain("clutch.co") is False
        assert is_non_company_domain("clutch.co") is True

    def test_a_subdomain_does_not_smuggle_a_denied_host_through(self) -> None:
        # "notwikipedia.org" must NOT match "wikipedia.org" — suffix matching
        # is on label boundaries only.
        assert is_non_company_domain("notwikipedia.org") is False


class TestListingDetection:
    @pytest.mark.parametrize(
        "title",
        [
            "The 10 Best Animation Studios in Dubai - 2026 Reviews",
            "Top 3D Animation Companies in the United Arab Emirates",
            "Top 15+ Animation Studios In Dubai (2026)",
            "20 best animation agencies in Dubai",
            "Top 5 Best Animation Studios in Dubai",
            "The Best Animation Video Production Companies in Dubai",
            "10 Design Agencies To Watch",
            "List of animation studios",
        ],
    )
    def test_listicle_titles_are_flagged(self, title: str) -> None:
        assert looks_like_listing_page(title=title) is True

    def test_listing_url_path_is_a_hint_even_without_a_listicle_title(self) -> None:
        assert (
            looks_like_listing_page(
                title="Animation", url="https://example.com/blog/animation-studios"
            )
            is True
        )

    def test_a_plain_company_homepage_title_is_not_flagged(self) -> None:
        assert (
            looks_like_listing_page(title="Blink Studios", url="https://blinkstudios.ae") is False
        )


class TestCompanyNameValidation:
    @pytest.mark.parametrize(
        "name",
        [
            "The 10 Best Animation Studios in Dubai - 2026 Reviews",
            "Top 15+ Animation Studios In Dubai (2026)",
            "What are the top-rated animation studios in the UAE?",
            "Which agency should I hire",
            "clutch.co",
            "https://example.com",
            "hello@example.com",
            "Home",
            "Contact Us",
            "Wikipedia",
            "Quora",
            "Instagram",
            "404 Not Found",
            "2026",
            # Prose captured from a long article instead of an entity
            # (observed live when extracting from a Wikipedia industry page).
            "UAE began to attract South Asian films",
            "the company was founded in Dubai",
            "",
            "   ",
            None,
            "A" * 200,
        ],
    )
    def test_non_company_names_are_rejected(self, name: str | None) -> None:
        assert is_valid_company_name(name) is False

    @pytest.mark.parametrize(
        "name",
        [
            "Northbeam Studio",
            "Vantage Motion Co.",
            "Harbor & Co. Consulting",
            "Infinity Animations",
            "Village Talkies",
            "Blink Studios",
            "Pixel & Pine",
            "3M",
            # Multi-word names whose lowercase words are legitimate
            # connectors must survive the sentence-fragment check.
            "Bank of America",
            "Victoria and Albert Museum",
            "Lammtara Art Production",
            "Nested VFX FZ-LLC",
            "Dubai International Film Festival",
        ],
    )
    def test_real_company_names_are_accepted(self, name: str) -> None:
        assert is_valid_company_name(name) is True


class TestCleanCompanyName:
    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Top Animation Studio In Dubai - Infinity Animations", "Infinity Animations"),
            ("Blink Studios | An Independent Film and Animation Studio", "Blink Studios"),
            ("Animation studio in Dubai - Captain Studio", "Captain Studio"),
            ("Northbeam Studio", "Northbeam Studio"),
        ],
    )
    def test_recovers_the_brand_from_an_seo_title(self, title: str, expected: str) -> None:
        assert clean_company_name(title) == expected

    @pytest.mark.parametrize(
        "title",
        [
            "The 10 Best Animation Studios in Dubai - 2026 Reviews",
            "Top 15+ Animation Studios In Dubai (2026)",
            "What are the top-rated animation studios in the UAE? - Quora",
            "Animation Studio UAE (@animationstudiouae) - Instagram",
            "",
        ],
    )
    def test_returns_none_rather_than_a_page_title(self, title: str) -> None:
        # The caller must treat None as "cannot name this company" and drop
        # the candidate — never fall back to the raw title.
        assert clean_company_name(title) is None


class TestSameSite:
    """The invariant that no denylist can cover.

    A company listed on an aggregator can never have that aggregator as its
    own website. Observed live: investing.com's Karachi-30 index page linked
    each constituent to an internal profile page, so "Attock Refinery" was
    created with domain `investing.com` — and again with `uk.investing.com`,
    because a country front-end looked like a different company.
    """

    @pytest.mark.parametrize(
        ("a", "b"),
        [
            ("investing.com", "uk.investing.com"),
            ("uk.investing.com", "investing.com"),
            ("www.investing.com", "investing.com"),
            ("m.investing.com", "uk.investing.com"),
            ("tracxn.com", "tracxn.com"),
            ("blog.example.com", "example.com"),
        ],
    )
    def test_front_ends_of_one_site_are_the_same_site(self, a: str, b: str) -> None:
        assert same_site(a, b) is True

    @pytest.mark.parametrize(
        ("a", "b"),
        [
            ("attockrefinery.com.pk", "investing.com"),
            ("northbeamstudio.example", "agencyroundup.example"),
            ("example.com", "notexample.com"),
            ("", "investing.com"),
        ],
    )
    def test_genuinely_different_sites_are_not(self, a: str, b: str) -> None:
        assert same_site(a, b) is False


class TestAggregatorDenylist:
    @pytest.mark.parametrize(
        "domain",
        [
            # Financial-data hosts: a stock index page otherwise turns every
            # constituent into a lead domained to the quote site.
            "investing.com",
            "uk.investing.com",
            "tradingview.com",
            "marketwatch.com",
            "psx.com.pk",
            # Startup/company databases whose profile pages look like
            # company pages.
            "tracxn.com",
            "cbinsights.com",
            "dealroom.co",
            "wellfound.com",
            "opencorporates.com",
        ],
    )
    def test_aggregators_can_never_be_leads(self, domain: str) -> None:
        assert is_non_company_domain(domain) is True


class TestNeverFetch:
    @pytest.mark.parametrize(
        "domain",
        ["facebook.com", "www.facebook.com", "scribd.com", "instagram.com", "linkedin.com"],
    )
    def test_login_walled_hosts_are_skipped_before_paying_to_fetch(self, domain: str) -> None:
        assert should_never_fetch(domain) is True

    @pytest.mark.parametrize("domain", ["clutch.co", "tracxn.com", "en.wikipedia.org"])
    def test_ordinary_directories_are_still_mined(self, domain: str) -> None:
        # These can't be leads, but their content is worth reading.
        assert should_never_fetch(domain) is False
        assert is_non_company_domain(domain) is True


class TestDomainVerification:
    """A lead pointing at a stranger's website is worse than no lead.

    Resolving a site by searching "<name> official website" is noisy: live
    runs returned website.com, canva.com and flysfo.com (San Francisco
    airport) for real Pakistani companies.
    """

    @pytest.mark.parametrize(
        ("name", "domain"),
        [
            ("Fauji Cement Company", "fccl.com.pk"),
            ("D G Khan Cement Company", "dgcement.com"),
            ("Engro Holdings", "engro-global.com"),
            ("Northbeam Studio", "northbeamstudio.example"),
            ("Attock Refinery Limited", "arl.com.pk"),
        ],
    )
    def test_a_matching_host_is_preferred(self, name: str, domain: str) -> None:
        assert domain_matches_company(name, domain) is True

    @pytest.mark.parametrize(
        ("name", "domain"),
        [
            ("Fauji Fertilizer Company", "website.com"),
            ("Attock Refinery", "canva.com"),
            ("Fauji Cement Company", "flysfo.com"),
        ],
    )
    def test_an_unrelated_host_does_not_match(self, name: str, domain: str) -> None:
        assert domain_matches_company(name, domain) is False


class TestPageMentionsCompany:
    """The decisive check, run against the page we fetch anyway."""

    def test_a_companys_own_page_mentions_it(self) -> None:
        assert page_mentions_company(
            "Attock Refinery",
            "Attock Refinery Limited (ARL) is one of Pakistan's oldest refineries.",
        )

    def test_suffix_differences_are_tolerated(self) -> None:
        # "Attock Refinery" vs "Attock Refinery Limited" is the same company.
        assert page_mentions_company("Attock Refinery Limited", "Welcome to Attock Refinery.")

    def test_an_unrelated_page_is_rejected(self) -> None:
        assert not page_mentions_company(
            "Fauji Fertilizer Company", "Canva: Visual Suite for Everyone. Design anything."
        )

    def test_generic_words_alone_never_match(self) -> None:
        # "Company"/"Services" must not make any page look like a match.
        assert not page_mentions_company(
            "Fauji Fertilizer Company", "Our company offers services and solutions."
        )

    def test_a_name_with_nothing_distinctive_is_not_blocked_here(self) -> None:
        # Scoring still has to find real evidence; this gate stays out of
        # the way rather than silently dropping a real company.
        assert page_mentions_company("AB Co", "Some unrelated text.")


class TestInstitutionalDomains:
    """Government/academic hosts are institutions, never prospects.

    Enumerating suffixes missed `karachi.mfa.gov.sg` (a consulate), which
    became a lead in a live run because the list had `.gov.uk` and `.gov.ae`
    but not `.gov.sg`. The check is on trailing labels instead.
    """

    @pytest.mark.parametrize(
        "domain",
        [
            "karachi.mfa.gov.sg",
            "dubai.gov.ae",
            "whitehouse.gov",
            "education.gouv.fr",
            "mit.edu",
            "ox.ac.uk",
            "army.mil",
        ],
    )
    def test_institutions_are_never_leads(self, domain: str) -> None:
        assert is_non_company_domain(domain) is True

    @pytest.mark.parametrize(
        "domain",
        [
            # A company is not an institution just because its NAME contains
            # one of those words.
            "government-solutions.com",
            "education.com",
            "acme.com",
            "eliteservices.pk",
            "arl.com.pk",
        ],
    )
    def test_ordinary_companies_are_not_caught(self, domain: str) -> None:
        assert is_non_company_domain(domain) is False
