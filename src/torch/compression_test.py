from pomagma.compiler.expressions import Expression
from pomagma.torch.compression import CompressionConfig, beta_compress
from pomagma.torch.corpus import ObTree
from pomagma.torch.language import Language
from pomagma.torch.structure import Structure


def test_beta_compress_basic(structure: Structure, language: Language):
    """Test basic beta compression functionality."""
    # Create some simple ObTrees that share common patterns
    # Use actual Obs from the real structure
    obtrees = [
        ObTree(
            name="APP",
            args=(
                ObTree(ob=structure.nullary_functions["S"]),
                ObTree(ob=structure.nullary_functions["K"]),
            ),
        ),
        ObTree(
            name="APP",
            args=(
                ObTree(ob=structure.nullary_functions["S"]),
                ObTree(ob=structure.nullary_functions["J"]),
            ),
        ),
        ObTree(
            name="COMP",
            args=(
                ObTree(
                    name="APP",
                    args=(
                        ObTree(ob=structure.nullary_functions["S"]),
                        ObTree(ob=structure.nullary_functions["K"]),
                    ),
                ),
                ObTree(ob=structure.nullary_functions["R"]),
            ),
        ),
    ]

    config = CompressionConfig(
        min_pattern_frequency=2,
        min_pattern_size=2,
        max_iterations=3,
        compression_threshold=0.0,  # Accept any benefit
    )

    # Compute probabilities once
    probs = language.compute_probs(structure)

    # Apply compression
    equation_benefits = beta_compress(structure, language, probs, obtrees, config)

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
    # Create obtrees with no shared subexpressions
    obtrees = [
        ObTree(ob=structure.nullary_functions["S"]),
        ObTree(ob=structure.nullary_functions["K"]),
        ObTree(ob=structure.nullary_functions["J"]),
    ]

    probs = language.compute_probs(structure)
    equation_benefits = beta_compress(structure, language, probs, obtrees)

    # Should find no patterns to compress
    assert equation_benefits == {}


def test_compression_config():
    """Test compression configuration."""
    config = CompressionConfig(
        min_pattern_frequency=3,
        min_pattern_size=4,
        max_iterations=10,
        compression_threshold=0.5,
    )

    assert config.min_pattern_frequency == 3
    assert config.min_pattern_size == 4
    assert config.max_iterations == 10
    assert config.compression_threshold == 0.5


def test_beta_compress_ranking(structure: Structure, language: Language):
    """Test that equations can be ranked by benefit."""
    # Create obtrees with patterns of different frequencies
    s_ob = structure.nullary_functions["S"]
    k_ob = structure.nullary_functions["K"]
    j_ob = structure.nullary_functions["J"]

    obtrees = [
        # Common pattern (freq=3): APP(S, K)
        ObTree(name="APP", args=(ObTree(ob=s_ob), ObTree(ob=k_ob))),
        ObTree(name="APP", args=(ObTree(ob=s_ob), ObTree(ob=k_ob))),
        ObTree(name="APP", args=(ObTree(ob=s_ob), ObTree(ob=k_ob))),
        # Less common pattern (freq=2): COMP(K, J)
        ObTree(name="COMP", args=(ObTree(ob=k_ob), ObTree(ob=j_ob))),
        ObTree(name="COMP", args=(ObTree(ob=k_ob), ObTree(ob=j_ob))),
    ]

    config = CompressionConfig(min_pattern_frequency=2, compression_threshold=0.0)

    probs = language.compute_probs(structure)
    equation_benefits = beta_compress(structure, language, probs, obtrees, config)

    if equation_benefits:
        # Should be able to sort equations by benefit
        sorted_equations = sorted(
            equation_benefits.items(), key=lambda x: x[1], reverse=True
        )

        # Highest benefit should be first
        best_equation, best_benefit = sorted_equations[0]
        assert isinstance(best_equation, Expression)
        assert isinstance(best_benefit, float)
        assert best_benefit >= 0.0
