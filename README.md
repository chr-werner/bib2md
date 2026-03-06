# bib2md

Sync BibLaTeX bibliography metadata into Obsidian Markdown note frontmatter.

Given a `.bib` file and a directory of Markdown notes, `bib2md` converts each bibliography entry into structured YAML and merges it into the frontmatter of the matching note. Authors are formatted as Obsidian wiki-links (`[[First Last]]`), groups become tags, and keywords become a list.

## bib2md — Requirements

- Python 3.10+
- [pybtex](https://pybtex.org/) (provides the `pybtex-convert` CLI)
- [PyYAML](https://pyyaml.org/)
- [python-frontmatter](https://github.com/eyeseast/python-frontmatter)

## bib2md — Installation

```bash
pip install -r requirements.txt
```

## bib2md — Usage

```bash
python bib2md.py <bib_file> <yaml_file> <md_directory>
```

| Argument       | Description                                                             |
| -------------- | ----------------------------------------------------------------------- |
| `bib_file`     | Path to the source `.bib` file                                          |
| `yaml_file`    | Path for the intermediate YAML file (created and deleted automatically) |
| `md_directory` | Root directory containing your Markdown notes                           |

```bash
python bib2md.py library.bib /tmp/library.yaml ~/obsidian/vault/papers/
```

## Note matching

Each Markdown file is matched to a bibliography entry by filename. The leading `@` and file extension are stripped, and the name is lowercased before lookup.

| Filename            | Matched entry key |
| ------------------- | ----------------- |
| `@doe2024.md`       | `doe2024`         |
| `@Einstein1905.md`  | `einstein1905`    |

Files with no matching entry are skipped with a warning.

## Frontmatter behaviour

- **Scalar fields** (title, year, journal, …) are created or overwritten.
- **List fields** (authors, tags, keywords) are merged — existing entries are kept and only new unique values are appended.

Example output frontmatter:

```yaml
title: On the Electrodynamics of Moving Bodies
authors:
  - "[[Albert Einstein]]"
year: 1905
tags:
  - physics
  - relativity
keywords:
  - special relativity
  - electrodynamics
```

## Running tests

```bash
pytest
```
