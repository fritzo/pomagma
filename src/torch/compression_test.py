from pomagma.compiler.expressions import Expression
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.torch.compression import beta_compress
from pomagma.torch.corpus import ObTree
from pomagma.torch.language import Language
from pomagma.torch.structure import Structure


def test_beta_compress_basic(structure: Structure, language: Language):
    """Test basic beta compression functionality."""
    # Create some simple ObTrees that share common patterns
    expr_strings = [
        "APP S K",
        "APP S J",
        "COMP APP S K APP S K",
        "COMP APP S K APP S J",
        "COMP COMP K J COMP K J",
    ]
    exprs = [parse_string_to_expr(expr_string) for expr_string in expr_strings]
    obtrees = [ObTree.from_expr(structure, expr) for expr in exprs]

    # Compute probabilities once
    probs = language.compute_probs(structure)

    # Apply compression with new simplified interface
    equation_benefits = beta_compress(structure, language, probs, obtrees)

    # Should return a dictionary mapping equations to benefits
    assert isinstance(equation_benefits, dict)

    # Each key should be an equation (EQUAL expression)
    for equation, benefit in equation_benefits.items():
        assert isinstance(equation, Expression)
        assert equation.name == "EQUAL"
        assert len(equation.args) == 2  # EQUAL has 2 arguments
        assert isinstance(benefit, float)
        assert benefit >= 0.0  # Benefits should be non-negative


def test_beta_compress_empty_input(structure: Structure, language: Language):
    """Test beta compression with empty input."""
    probs = language.compute_probs(structure)
    equation_benefits = beta_compress(structure, language, probs, [])
    assert equation_benefits == {}


def test_beta_compress_no_patterns(structure: Structure, language: Language):
    """Test beta compression when no common patterns exist."""
    # Create obtrees with no shared subexpressions or insufficient repetition
    obtrees = [
        ObTree(ob=structure.nullary_functions["S"]),
        ObTree(ob=structure.nullary_functions["K"]),
        ObTree(ob=structure.nullary_functions["J"]),
    ]

    probs = language.compute_probs(structure)
    equation_benefits = beta_compress(structure, language, probs, obtrees)

    # Should find no patterns to compress (atomic expressions have no repeated
    # subexpressions)
    assert equation_benefits == {}


def test_beta_compress_single_obtree(structure: Structure, language: Language):
    """Test beta compression on a single obtree with internal patterns."""
    expr_strings = [
        "COMP APP S K APP S K",
        "COMP APP S K APP S J",
    ]
    exprs = [parse_string_to_expr(expr_string) for expr_string in expr_strings]
    obtrees = [ObTree.from_expr(structure, expr) for expr in exprs]

    probs = language.compute_probs(structure)
    equation_benefits = beta_compress(structure, language, probs, obtrees)

    assert isinstance(equation_benefits, dict)

    for equation, benefit in equation_benefits.items():
        assert isinstance(equation, Expression)
        assert equation.name == "EQUAL"
        assert isinstance(benefit, float)
        assert benefit >= 0.0


def test_beta_compress_ranking(structure: Structure, language: Language):
    """Test that equations can be ranked by benefit."""
    expr_strings = [
        "APP S K",
        "COMP APP S K APP S K",
        "COMP COMP K J COMP K J",
    ]
    exprs = [parse_string_to_expr(expr_string) for expr_string in expr_strings]
    obtrees = [ObTree.from_expr(structure, expr) for expr in exprs]

    probs = language.compute_probs(structure)
    equation_benefits = beta_compress(structure, language, probs, obtrees)

    if equation_benefits:
        sorted_equations = sorted(
            equation_benefits.items(), key=lambda x: x[1], reverse=True
        )
        best_equation, best_benefit = sorted_equations[0]
        assert isinstance(best_equation, Expression)
        assert isinstance(best_benefit, float)
        assert best_benefit >= 0.0


def test_obtree_materialize(structure: Structure, language: Language):
    """Test the new ObTree.materialize method."""
    # Create a simple obtree
    obtree = ObTree(
        name="APP",
        args=(
            ObTree(ob=structure.nullary_functions["S"]),
            ObTree(ob=structure.nullary_functions["K"]),
        ),
    )

    # Materialize to dense tensor
    tensor = obtree.materialize(structure)

    # Should be the right shape
    assert tensor.shape == (structure.item_count + 1,)

    # Should have non-zero entries for the E-classes that appear
    s_ob = structure.nullary_functions["S"]
    k_ob = structure.nullary_functions["K"]

    assert tensor[s_ob].item() == 1.0  # S appears once
    assert tensor[k_ob].item() == 1.0  # K appears once

    # Most entries should be zero
    assert (tensor == 0.0).sum().item() >= structure.item_count - 2
