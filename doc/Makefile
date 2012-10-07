all: architecture.pdf

GRAPHVIZ=dot

architecture.pdf: architecture.dot FORCE
	$(GRAPHVIZ) -T pdf architecture.dot -o architecture.pdf
	$(GRAPHVIZ) -T png architecture.dot -o architecture.png

FORCE:
