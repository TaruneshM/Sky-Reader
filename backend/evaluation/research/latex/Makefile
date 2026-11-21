all: paper.pdf

paper.pdf: paper.tex references.bib
	pdflatex -interaction=nonstopmode paper
	bibtex paper
	pdflatex -interaction=nonstopmode paper
	pdflatex -interaction=nonstopmode paper

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.toc *.pdf
