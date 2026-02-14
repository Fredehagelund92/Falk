# Changelog

All notable changes to falk will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- MCP server (`falk mcp`) for Cursor and Claude Desktop integration
- Comprehensive `falk test` command for project validation and testing
- `display_name` field in semantic layer for business-friendly dimension labels
- WHERE clause parsing for natural language filters
- Slack bot with user tagging and proper markdown formatting
- Sample DuckDB data generation on `falk init`
- Windows encoding compatibility (UTF-8 support)

### Changed
- Moved agent functionality from CLI to MCP server
- CLI now focused on project management and testing
- Removed direct query commands (`query`, `decompose`, `lookup`, etc.)
- Replaced `falk eval` with more comprehensive `falk test`
- Removed `falk sync` command (merged into `falk test`)

### Removed
- Backward compatibility code for old project structures
- Legacy `context/` directory
- Unused modules: `repository_sync.py`, `quality.py`, `web.py`
- Example setup code (`example.py`)

### Fixed
- Unicode encoding errors on Windows
- Slack message formatting (proper bullets and user tagging)
- Scaffold completeness (customer_segment dimension, proper semantic_models.yaml format)
- Project validation error messages

## [0.1.0] - TBD

Initial release.
