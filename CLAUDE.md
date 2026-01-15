# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**NEVER** update this file during a working session. Use `docs/LESSONS.md` to track project learnings and `docs/TECHNICAL_DETAILS.md` for development documentation.

<!-- This repo is designed to be used with the FLUX framework: https://github.com/carveragents/flux -->

---

## Project Overview

**Carver Feeds SDK** is a Python library providing access to the Carver Feeds API for regulatory feed data. Published to PyPI as `carver-feeds-sdk`, it's a production-ready library with comprehensive error handling, type hints, and documentation.

## Specialized Sub-Agents Available

**ALWAYS** 
1. Use the appropriate specialized sub-agents available for the task being worked on. 
2. Provide the specialized sub-agents with the current working session goal. 
3. Run the Python Code Reviewer agent after each code change and have the Python Expert fix any issues found.

- **python-code-reviewer**: Review any new or modified Python code for quality, maintainability, and adherence to best practices. 
- **python-expert**: Write and test all Python code for the library.

## Important Reference Files

- Starting point to understand the project is: [docs/README.md](docs/README.md)
- Important lessons learned and pitfalls to avoid: [docs/LESSONS.md](docs/LESSONS.md)