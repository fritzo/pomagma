all: architecture.pdf

architecture.pdf: architecture.dot FORCE
	neato -T pdf architecture.dot -o architecture.pdf
	@#dot -T pdf architecture.dot -o architecture.pdf

FORCE:
