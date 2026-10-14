# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-14

### Added
- **Cross-Platform Git Mining Engine (`miner.py`)**:
  - Pure Python standard library extraction via native `git log --numstat --date=iso --pretty=format:... --no-merges`.
  - Zero external dependencies (no GitPython, no Pandas, no Rich), achieving sub-20ms cold CLI startup.
  - Robust UTF-8 handling with character recovery on non-standard Windows consoles.
  - Normalization for Git rename paths (`{old => new}` and `old => new`).
  - Automatic filtering of binary files (`- -`).
  - Streaming iterator mode (`stream_commits`) for constant $O(1)$ memory streaming across huge repos.
- **Bus Factor & Knowledge Silo Analyzer (`busfactor.py`)**:
  - Computes authorship distribution per file across commit history.
  - Flags single-point-of-failure files ($\ge 75\%$ contribution from single author with $\ge 3$ revisions).
  - Summarizes top organizational bottleneck authors across the codebase.
- **Architectural Hotspots Engine (`hotspots.py`)**:
  - Correlates revision change frequency (churn) with net lines added/deleted.
  - Evaluates risk score using non-linear curve: $\log(1 + \text{churn}) \times \sqrt{\max(5, \text{added} - \text{deleted})}$.
  - Categorizes files into `CRITICAL`, `HIGH`, `MEDIUM`, and `LOW` risk tiers.
- **Temporal Coupling Analyzer (`coupling.py`)**:
  - Detects implicit architectural dependencies by tracking co-change frequencies between file pairs.
  - Automatically filters large bulk commits ($> 25$ files) to eliminate noise from lockfiles and broad formatting sweeps.
  - Calculates coupling percentage based on minimum revision counts.
- **Composite Health Scoring Engine (`scorer.py`)**:
  - Computes an objective 0–100 codebase health score factoring in bus factor distribution, hotspot density, coupling debt, and single-author repo penalties.
  - Assigns letter grades (`A`, `B`, `C`, `D`, `F`) and human-readable diagnostic verdicts.
- **Multi-Format Renderers (`formatter.py`)**:
  - Colorized ANSI terminal dashboard with visual score meter and aligned tables.
  - Plaintext ASCII fallback mode (`--ascii`, `--no-color`, or `NO_COLOR=1`).
  - PR-ready GitHub-flavored Markdown generator for pull request quality gates and summaries.
  - Machine-readable structured JSON format for programmatic CI ingestion.
- **CLI Subcommand Suite (`cli.py`)**:
  - `repopulse audit [PATH]` (Full forensic health audit).
  - `repopulse busfactor [PATH]` (Dedicated bus factor analysis).
  - `repopulse hotspots [PATH]` (Dedicated hotspot & churn analysis).
  - `repopulse coupling [PATH]` (Dedicated temporal coupling analysis).
  - Flags: `--since`, `-n / --max-commits`, `--fail-under <SCORE>`, `--json`, `--markdown`, `--summary`, `--export / -o`, `--no-color`, `--ascii`.
- **GitHub Marketplace Composite Action (`action.yml`, `action.py`)**:
  - Marketplace action specification (`name: 'RepoPulse Git Forensic Health Audit'`, `branding: {icon: 'activity', color: 'red'}`).
  - Inputs (`path`, `fail-under`, `summary`, `since`, `max-commits`, `export-file`).
  - Outputs (`health-score`, `bus-factor-alerts`, `hotspot-count`).
  - Automatically posts rich Markdown health summary cards to `$GITHUB_STEP_SUMMARY`.

## [0.1.0] - 2026-10-14

### Added
- Initial project prototype and experimental git log parsing.
