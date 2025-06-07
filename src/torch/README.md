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

### Rule Counting
The `compute_rules` method uses Eisner's **gradient trick**<sup>1</sup> to count the expected number of times each grammar production rule is used to generate observed E-class frequencies.

Given observed counts/weights for each E-class (the `data` parameter), this method computes how frequently each grammar rule was used in generating those observations.

**Algorithm:**
1. Compute E-class probabilities using current grammar weights: `probs = compute_probs(structure)`
2. Compute log-likelihood of observed data: $\mathcal{L} = \sum_i \text{data}[i] \cdot \log(\text{probs}[i])$
3. Take gradients with respect to grammar parameters: $\nabla_w \mathcal{L}$
4. Scale gradients by current weights to get expected rule usage counts

**Mathematical Foundation:**
Eisner's key insight is that for log-linear (exponential family) distributions, the gradient of log-likelihood with respect to parameters equals expected feature counts:
$$\frac{\partial}{\partial w} \log P(\text{data} | w) = \mathbb{E}[\text{count of grammar rule } w \text{ used in generating data}]$$

This allows computing expected rule usage without explicitly enumerating all possible derivations that could generate the observed E-class frequencies.

### Occurrence Counting
The `compute_occurrences` method counts total occurrences of each subexpression (E-class) across all parse trees of observed expressions, weighted by grammar probabilities. Unlike `compute_rules` which counts only leaf nodes, this counts **all subexpressions** including internal nodes.

**Algorithm:** Backward propagation through the E-graph
1. Compute forward probabilities: `probs = compute_probs(structure)`
2. Initialize: `counts[i] = data[i]` (observed occurrences)  
3. Iterate until convergence: for each E-node `f(l,r) = v`, distribute parent occurrences to children:
   $$\text{counts}[l] \mathrel{+}= \frac{w_f \cdot \text{probs}[l] \cdot \text{probs}[r] \cdot \text{counts}[v]}{\text{probs}[v]}$$

### Extraction
The `extract_all` method implements **E-graph extraction**—finding the single best (highest probability) concrete expression for each E-class. This converts the compact E-graph representation back to explicit syntax trees by selecting one representative from each equivalence class.

**Algorithm:** Extraction proceeds in two phases:
1. **`compute_best`**: A max-product analog of `compute_probs` that finds the highest probability derivation for each E-class. Like `compute_probs`, it iterates until convergence, but uses `max` instead of `sum`:
   $$\text{best}[v] \leftarrow \max\left(w_{\text{nullary}}[v], \max_{f} w_f \max_{\substack{(l,r): \\ f(l,r) = v}} \text{best}[l] \cdot \text{best}[r]\right)$$

2. **Extraction**: Sort E-classes by descending `best` probability (which gives a valid topological order since compound expressions have probability ≤ min(dependency probabilities)), then greedily select the highest-probability decomposition for each E-class.

### Grammar Fitting
The `fit` method uses **gradient descent with L1 regularization** to fit normalized PCFG weights to observed corpus data while controlling sparsity.

**Algorithm:**
1. **Convert corpus** to E-class frequency data: `data[i]` = observed count of E-class `i`
2. **Objective function**: `Loss = -log P(data | grammar) + λ ||nullary_functions||₁`
   - Log-likelihood term encourages fitting the observed frequencies
   - L1 penalty term controls sparsity of nullary function weights
3. **Gradient descent**: Use L-BFGS optimizer with warm-started `compute_probs`
4. **Constraints**: After each step, project to feasible set:
   - **Nonnegativity**: `weights ← max(weights, 0)`
   - **Normalization**: `weights ← weights / weights.sum()`

**Key features:**
- **Warm starting**: Each `compute_probs` call is initialized with results from the previous step, reducing iteration count
- **Sparsity control**: L1 regularization automatically sets low-frequency terms to zero
- **Automatic differentiation**: Gradients computed through the iterative E-graph propagation

**Mathematical Foundation:**
The log-likelihood term is computed as:
$$\log P(\text{data} | \text{grammar}) = \sum_i \text{data}[i] \cdot \log(\text{probs}[i])$$
where `probs` comes from `compute_probs`. The gradient flows back through the entire iterative fixed-point computation via PyTorch's autograd.

### References
1. Jason Eisner (2016)
  "Inside-Outside and Forward-Backward Algorithms are Just Backprop"
  <https://www.cs.jhu.edu/~jason/papers/eisner.spnlp16.pdf>