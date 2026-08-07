# Changelog

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries are not written by hand. Each pull request that changes behaviour drops
a fragment into `changelog.d/`, named `<issue>.<type>.md` — where `<type>` is one
of `added`, `changed`, `deprecated`, `removed`, `fixed`, `security` — and the
release assembles them:

```bash
uv run towncrier build --version "$(uv version --short)"
```

The issue link comes free from the filename, which turns this file into a
navigable index of the decisions that produced it.

<!-- towncrier release notes start -->

## [0.0.2] - 2026-08-05

### Fixed

- Publishing metadata pointed at a repository that answered 404 to anonymous
  callers. ([#24](https://github.com/panlabs-tech/overpower/issues/24))

## [0.0.1] - 2026-08-05

The `0.0.x` series is not the product. It reserves the name on PyPI and proves
the publishing pipeline end to end; it installs nothing.

### Added

- Name reserved on PyPI, published from GitHub Actions through a trusted
  publisher, with no credential stored anywhere.
  ([#13](https://github.com/panlabs-tech/overpower/issues/13))
- `overpower` reports the version that arrived, the interpreter that ran it, the
  platform and the payload that crossed — the four facts only a real execution
  can answer. ([#13](https://github.com/panlabs-tech/overpower/issues/13))
