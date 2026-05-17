"""Compare ibflex.Types annotations against the IBKR Activity Flex Query
Reference. Prints any field names mentioned in the reference HTML that don't
appear as attributes on any FlexElement subclass.

Usage:
    python scripts/check_schema_drift.py

Exit code:
    0 if every reference field maps to a known attribute (or is a known
      alias / known-omitted field per the IGNORED set).
    1 if drift is detected; the report lists candidates.

This is heuristic — IBKR's HTML is not strictly structured, and field names
are scraped out of <code>/<th>/<td> tags by case-insensitive token matching.
False positives are expected; the goal is a quick "anything new since last
run?" signal, not a precise spec checker.
"""
from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

# Add project root to path so this runs from `python scripts/check_schema_drift.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ibflex import Types

REFERENCE_URL = (
    "https://www.interactivebrokers.com/en/software/reportguide/"
    "reportguide.htm"
)
# Keep this lowercase; matches are case-insensitive.
IGNORED = {
    # Sentinels used by IBKR but never an attribute name we'd expect.
    "yes", "no", "y", "n", "true", "false", "null", "none", "all",
    # XML structural words.
    "flexqueryresponse", "flexstatement", "flexstatements",
    # Common English noise from prose.
    "the", "and", "for", "with", "field", "fields", "report", "reports",
}


def fetch_reference_html(url: str = REFERENCE_URL) -> str:
    """Fetch data from URL."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "ibflex2-schema-drift/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_candidate_fields(html: str) -> set[str]:
    """Pull camelCase / PascalCase tokens out of the HTML. The IBKR Reference
    presents field names inside <code> and <td> tags; this captures both."""
    # camelCase tokens (lowercase first letter, at least one uppercase later)
    pattern = re.compile(r"\b[a-z][a-zA-Z0-9]{2,}\b")
    tokens = set(pattern.findall(html))
    # Filter to tokens with mixed case (real field names) or known acronyms.
    return {
        t for t in tokens
        if (any(c.isupper() for c in t[1:]))
        and t.lower() not in IGNORED
    }


def known_attributes() -> set[str]:
    """Every attribute name across every FlexElement dataclass."""
    attrs: set[str] = set()
    for name in dir(Types):
        cls = getattr(Types, name)
        if not (isinstance(cls, type) and issubclass(cls, Types.FlexElement)):
            continue
        for klass in cls.__mro__:
            attrs.update(getattr(klass, "__annotations__", {}).keys())
    # Drop noise from FlexElement / FlexStatement container attrs.
    return {a for a in attrs if not a[0].isupper()}


def main() -> int:
    """Checks whether the schema on IBKR side has changed compared to the maps."""
    html = fetch_reference_html()
    candidates = extract_candidate_fields(html)
    known = known_attributes()
    drift = sorted(candidates - known)

    if not drift:
        print("No drift detected: every camelCase token in the IBKR "
              "reference maps to a known attribute.")
        return 0

    print(f"Possible drift: {len(drift)} candidate field names from the "
          f"IBKR reference are not declared on any FlexElement subclass.")
    print()
    print("Candidates (heuristic; may include false positives):")
    for name in drift:
        print(f"  {name}")
    print()
    print("Triage: for each real new field, add it to the appropriate "
          "dataclass in ibflex/Types.py and add a fixture/test.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
