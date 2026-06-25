# english-gaokao-test-creator

A Claude skill for creating original English test papers aligned with China's New Gaokao I format.

## Features

- Crawl recent articles from foreign news sources (NPR, The Guardian, etc.)
- Save raw corpus as Markdown with YAML frontmatter
- Generate an HTML briefing with collapsible article summaries
- Produce Word documents containing:
  - Listening scripts and questions
  - Reading comprehension and gap-filling (七选五)
  - Cloze and grammar fill-in-the-blank
  - Writing prompts (practical writing + continuation writing)
  - Answer keys and analysis
  - Basic information form
- Support user-defined themes and selectable test parts

## Usage

This repository is designed to be used as a Claude skill. Place the folder in your Claude skills directory (usually `~/.claude/skills/`) and invoke it when you need to generate test papers.

## Scripts

- `scripts/crawl_corpus.py` - Crawl news articles and generate HTML briefing
- `scripts/build_test_docx.py` - Build the final Word document from a JSON spec

## Install dependencies

```bash
pip install -r requirements.txt
```

## License

MIT
