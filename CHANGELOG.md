# Changelog

## Unreleased

### Breaking changes

- **`initialInvestment` field type changed from `Optional[decimal.Decimal]` to `Optional[bool]`**
  on `Trade`, `Lot`, `SymbolSummary`, `AssetSummary`, `Order`, `OptionEAE`, and `SecurityInfo`.
  IBKR sends `Yes`/`No` (or `Y`/`N`) for this attribute, not a numeric value, so the previous
  `Decimal` typing was incorrect and would raise `FlexParserError` on real-world data. Code
  doing arithmetic comparisons (`if trade.initialInvestment > 0:`) needs to be updated; under
  Python's `True > 0` semantics it would silently misbehave with the new type.
- type `FlexStatement.TransactionTaxes` as `Tuple[Union[TransactionTax, TransactionTaxDetail], ...]`
  instead of bare `Tuple`

### Added

- New `StockGrantActivity` dataclass mirroring `<StockGrantActivities>` and wired into
  `FlexStatement.StockGrantActivities`.
- Many new fields across existing dataclasses to match the current IBKR Flex Query schema:
  `figi`, `issuerCountryCode`, `costBasis`, `realizedPL`, `dividendType`, `settleDate`,
  `positionInstructionID`, `positionInstructionSetID`, `levelOfDetail`, `subCategory`,
  `orderId`, `cgtWithholdingAccruals*`, `liteSurchargeAccruals*`, `otherIncomeMTD`,
  `otherIncomeYTD`, etc.
- New enum values: `Code.LIQUIDATION_FORCED` (`'LF'`), `Code.ADR`, `OrderType.LIT`,
  `TransferType.OTC`.
- Parser accepts `Yes`/`No` in addition to `Y`/`N` for boolean attributes.
- Parser handles `MULTI` as a date/datetime value (returns `None`) for summary rows that
  span multiple dates.
- **Opt-in unknown-attribute tolerance** — call
  `ibflex.enable_unknown_attribute_tolerance()` to silently skip unknown XML attributes
  and element types instead of raising `FlexParserError`. Useful when IBKR adds new fields
  faster than the type definitions can be updated. Off by default; toggle with
  `disable_unknown_attribute_tolerance()`. Note: the flag is module-level global state and
  is **not thread-safe**.
- New subCategory plus newer IB attributes on `TransactionTaxDetail` (`figi`,
  `issuerCountryCode`, `settleDate`, `orderId`, `serialNumber`, `deliveryType`, `commodityType`,
  `fineness`, `weight`)

### Fixed

- `EquitySummaryByReportDateInBase.currency` was declared twice in the same dataclass.
- ~10 fields in `SymbolSummary` were declared twice (artifacts of a prior bad merge).
- `FlexQueryResponse.__repr__` was missing a comma between `len(FlexStatements)` and
  `Message`.
- `FlexStatement.__repr__` was silently broken under PEP 563 deferred annotations and
  showed no sequence lengths.

### Security

- Replaced stdlib `xml.etree.ElementTree` with `defusedxml` in both `parser.py` and
  `client.py`. Guards against XXE, billion-laughs, and external-entity attacks in
  Flex statement XML pulled from third-party sources. Adds `defusedxml>=0.7` as a
  required runtime dependency.

### Tests

- Hypothesis property tests for `prep_date`, `prep_time`, `prep_datetime` covering
  every IBKR-documented format combination across the entire 2000-2068 date range.
- Exhaustive parametrized matrix tests for every (date format × time format ×
  separator) combination, including `MULTI`, the legacy `", "` separator, and
  trailing-TZ-offset values.
- CI matrix expanded to `ubuntu-latest`, `macos-latest`, and `windows-latest`
  across Python 3.9-3.13.
- regression test for parsing `TransactionTaxDetail` with `subCategory`/`figi`/`issuerCountryCode`

### Docs

- New `CONTRIBUTING.md` with checklists for adding fields, adding dataclasses,
  adding enum values, anonymizing test data, and resolving upstream-sync
  conflicts.
- New `.github/PULL_REQUEST_TEMPLATE.md`.

### Test infrastructure (second wave)

- Fixture corpus under `tests/fixtures/` with anonymized full-document Flex
  XML samples (`minimal`, `activity_basic`, `stock_grant`, `crypto_transfer`,
  `legacy_separator`); `tests/test_fixtures.py` walks every file.
- Snapshot tests pin the parsed output of every fixture under
  `tests/snapshots/`. Update with `SNAPSHOT_UPDATE=1 pytest tests/test_snapshots.py`.
- `client.py` test coverage raised from 69% to 100% by mocking `requests`
  for every error-code branch, the timezone fallback, the
  `StatementGenerationTimeout` retry-exhausted path, the lazy-import error,
  and the CLI entrypoint.
- Coverage gate raised to 95% (project-wide currently at 99.4%).
- Pytest `filterwarnings` set to escalate `DeprecationWarning` and
  `PendingDeprecationWarning` so future-Python deprecations fail loudly.

### Polish

- New `parser.unknown_attribute_tolerance()` context manager for
  scope-limited tolerance toggling. Restores the previous flag value on
  exit (including on exception). The bare `enable_/disable_` helpers
  remain.
- `CFDCharge` dataclass now wired into `FlexStatement.CFDCharges` and
  exposed in `__all__`.
- Removed the unused `all_equal` helper from `ibflex.utils`.
- Stricter mypy: `warn_unreachable`, `warn_no_return`, `strict_equality`,
  `extra_checks` are now on.
- Updated stale `TODO - need types for:` list at the top of `Types.py`.

### CI / process

- Weekly **schema-drift workflow** (`.github/workflows/schema-drift.yml`)
  scrapes the IBKR Activity Flex Query Reference and opens a tracking
  issue if it finds field names not present in `ibflex.Types`.
- New `ibflex/schema_version.py` records the date of the last full audit
  against the IBKR reference (`SCHEMA_AUDIT_DATE`).
- New **`pip-audit`** job in CI scans dependencies for known
  vulnerabilities.
- New **CHANGELOG enforcement workflow** rejects PRs that touch
  `ibflex/*.py` without updating `CHANGELOG.md` (override with the
  `skip-changelog` label).
- New **Dependabot** config (`.github/dependabot.yml`) keeps pip
  dependencies and GitHub Actions versions current.
- New `SECURITY.md` describing the threat model and the private advisory
  reporting flow.
- New issue templates under `.github/ISSUE_TEMPLATE/` for parser errors,
  new IBKR fields, and bugs.
- New `README.rst` rewritten for this fork: covers the tolerance feature,
  `defusedxml`, supported Python versions, the `web` extra, and the
  `nix develop` workflow.

## 1.0.0 — 2026-04

Initial release of the `ibflex2` fork. See README for context on why this fork exists.
