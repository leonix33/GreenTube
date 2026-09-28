from app.catalog.normalize import dedupe_fingerprint, normalize_title, slugify


def test_slugify():
    assert slugify("Hip-Hop Flow!") == "hip-hop-flow"


def test_dedupe_fingerprint_stable():
    a = dedupe_fingerprint("Kofi Mensah", "Sunday Market", 34)
    b = dedupe_fingerprint("  kofi   mensah ", "Sunday   Market", 34)
    assert a == b


def test_normalize_title():
    assert normalize_title("  Hello   World ") == "hello world"
