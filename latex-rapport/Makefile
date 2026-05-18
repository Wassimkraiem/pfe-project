# ─── BVIRAL Platform PFE Report — Makefile ────────────────────────────────────
# Requires: pdflatex or lualatex, biber, latexmk
# Usage: make          → full build (pdflatex + biber + pdflatex × 2)
#        make quick    → single pdflatex pass (fast, no bib update)
#        make clean    → remove auxiliary files
#        make distclean → clean + remove PDF

MAIN     = main
LATEX    = pdflatex
BIBER    = biber
LATEXMK  = latexmk
LATEX_FLAGS = -interaction=nonstopmode -halt-on-error -shell-escape

.PHONY: all quick clean distclean

all:
	$(LATEXMK) -pdf -pdflatex="$(LATEX) $(LATEX_FLAGS)" $(MAIN)

quick:
	$(LATEX) $(LATEX_FLAGS) $(MAIN)

# Manual multi-pass build (if latexmk is unavailable)
manual:
	$(LATEX) $(LATEX_FLAGS) $(MAIN)
	$(BIBER) $(MAIN)
	$(LATEX) $(LATEX_FLAGS) $(MAIN)
	$(LATEX) $(LATEX_FLAGS) $(MAIN)

clean:
	$(LATEXMK) -c $(MAIN) 2>/dev/null || true
	rm -f *.aux *.bbl *.bcf *.blg *.fdb_latexmk *.fls *.lof *.log \
	       *.lot *.out *.run.xml *.toc *.xdv chapters/*.aux

distclean: clean
	rm -f $(MAIN).pdf
