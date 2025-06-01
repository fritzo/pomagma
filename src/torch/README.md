# Computing E-graph statistics with PyTorch

This module implements efficient computation over equality graphs (E-graphs) using PyTorch. It bridges techniques from term rewriting, universal algebra, and probabilistic context-free grammars (PCFGs) to enable differentiable computation over symbolic expressions.

### Background

The core idea is to represent a **combinatory algebra** as an **E-graph**—a data structure that compactly represents equivalence classes of terms under equational theories. We then define probabilistic grammars over this structure and implement efficient algorithms for:

- Computing probability distributions over equivalence classes (E-classes)
- Counting term occurrences using automatic differentiation  
- Optimizing grammar weights via gradient-based methods

This enables applications in program synthesis, symbolic mathematics, and automated reasoning where we need to work with large spaces of equivalent expressions.

Unlike traditional E-graph algorithms that focus on equality saturation, this framework computes probabilistic statistics over the existing E-graph structure.

## Data Types

### Ob (E-class Identifier)
```python
Ob = NewType("Ob", int)
```
An **E-class identifier** representing an equivalence class of terms in the E-graph. In universal algebra terminology, this corresponds to an element of the carrier set. Objects are 1-indexed with `0` representing undefined/empty.

### Structure (E-graph)
The `Structure` class represents an **E-graph** encoding a combinatory algebra. It stores:

- **Nullary functions** (constants): `φ: {} → Carrier`
- **Binary functions**: `f: Carrier × Carrier ⇀ Carrier` (partial functions)
- **Symmetric functions**: `g: Carrier × Carrier ⇀ Carrier` where `g(a,b) = g(b,a)`
- **Relations**: predicates over the carrier set

The E-graph compactly represents all terms that are equal under the equational theory. Each **E-node** `(L, R, V)` in a binary function represents the equation `f(L, R) = V`, meaning "applying function f to E-classes L and R yields E-class V."

### ObTree (Partially Parsed Expression)
An `ObTree` represents a **partially understood expression** where:
- Leaves are E-class identifiers (`Ob`) representing fully reduced subterms
- Internal nodes are function symbols whose arguments haven't been fully evaluated/reduced to E-classes in the current E-graph

This hybrid structure bridges the gap between raw syntax trees (from parsing) and fully reduced E-classes, allowing efficient representation of expressions during the reduction process.

### Language (Probabilistic Grammar)
The `Language` class represents probability weights that can be interpreted as either:
1. A **generative PCFG**: weights define probabilities for generating new terms
2. A **discriminative model**: weights represent observed frequencies in a corpus

It stores probability weights for:
```math
\begin{align}
&w_{\text{nullary}}[i] &&\text{(weight of nullary function producing E-class } i \text{)} \\
&w_f &&\text{(weight of binary or symmetric function } f \text{)} \\
\end{align}
```

## Algorithms

### Probability Propagation
The `compute_probs` method computes the **probability distribution over E-classes** given a normalized PCFG. This implements a fixed-point iteration:

**Algorithm:**
1. **Initialize** with atomic probabilities: $p[i] \leftarrow w_{\text{nullary}}[i]$ (for nullary functions only)
2. **Iterate** until convergence:
   $$p[v] \leftarrow w_{\text{nullary}}[v] + \sum_{f \in \text{Functions}} w_f \sum_{\substack{(l,r): \\ f(l,r) = v}} p[l] \cdot p[r]$$

This computes the marginal probability that a randomly generated term from the PCFG reduces to each E-class under the equational theory.

**Mathematical Interpretation:**
The iteration corresponds to computing the **least fixed point** of the operator:
$$\mathcal{T}(p)[v] = w_{\text{nullary}}[v] + \sum_{f} w_f \sum_{(l,r) \mapsto v} p[l] \cdot p[r]$$

For convergent PCFGs (where the total probability mass devoted to non-nullary productions is less than 1), this converges to the unique probability distribution over generated terms.

### Occurrence Counting (WIP)
The `compute_occurrences` method uses Eisner's **gradient trick**<sup>1</sup> to count expected occurrences of each E-class in expressions from a corpus.

While `compute_probs` computes the forward direction (grammar → E-class probabilities), `compute_occurrences` computes the backward direction (corpus expressions → expected E-class usage).

**Algorithm sketch:**
1. For each corpus expression represented as `ObTree`, compute $\nabla_p \log P(\text{tree} | p)$
2. This gradient gives the expected number of times each E-class appears in the expression, marginalized over all possible ways to extract the tree from the E-graph
3. Aggregate gradients across the corpus to get global occurrence statistics

**Mathematical Foundation:**
If $P(\text{tree} | p)$ is the probability of extracting a given tree from the E-graph under distribution $p$, then:
$$\frac{\partial}{\partial p[v]} \log P(\text{tree} | p) = \mathbb{E}[\text{count of E-class } v \text{ in tree extraction}]$$

This identity from the score function estimator allows us to compute occurrence expectations without explicitly enumerating all possible tree extractions from the E-graph.

### References
1. Jason Eisner (2016)
  "Inside-Outside and Forward-Backward Algorithms are Just Backprop"
  <https://www.cs.jhu.edu/~jason/papers/eisner.spnlp16.pdf>