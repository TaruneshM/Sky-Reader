# Sky Reader — IEEE LaTeX Source Package

This directory contains the complete IEEE-style LaTeX source code for the research paper:

**"Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment"**

## Contents
- `paper.tex`: Main LaTeX source document formatted to IEEEtran conference standard.
- `references.bib`: Verified BibTeX bibliography (16 entries).
- `figures/`: Vector SVGs of all 6 research figures.
- `Makefile`: Build automation for systems with TeX Live installed.

## Compilation Instructions

### Option 1: Local Compilation with TeX Live
If you have `pdflatex` and `bibtex` installed:
```bash
pdflatex paper
bibtex paper
pdflatex paper
pdflatex paper
```
Or using `latexmk`:
```bash
latexmk -pdf paper.tex
```

### Option 2: Overleaf
1. Compress this `latex/` directory into a `.zip` archive.
2. In Overleaf, click **New Project** -> **Upload Project**.
3. Select the `.zip` file. Overleaf will automatically detect `paper.tex` and compile using its native TeX Live environment.

### Option 3: Required TeX Live Packages
On Debian/Ubuntu systems, the required packages are:
```bash
sudo apt-get install texlive-latex-base texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra texlive-publishers
```
