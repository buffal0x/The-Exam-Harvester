# Lesson Scraper

A Linux-friendly scraper scaffold for authenticated learning platforms.

## Features

- Playwright-based login
- Saved authenticated browser state
- Crawlee-based traversal
- Config-driven extraction
- Raw HTML + screenshot + parsed JSON + Markdown output
- URL allow/deny filtering

## Structure

```text
lesson-scraper/
├─ app/
├─ config/
├─ data/
│  ├─ auth/
│  ├─ raw/
│  ├─ parsed/
│  └─ manifests/
├─ logs/
├─ requirements.txt
└─ README.md
