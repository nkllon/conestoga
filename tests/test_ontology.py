import pytest


def test_ontology_shapes_optional():
    try:
        from pyshacl import validate
        from rdflib import Graph
    except ImportError:
        pytest.skip("pyshacl not installed")

    g = Graph()
    g.parse("ontology/conestoga.ttl", format="turtle")
    conforms, results_graph, results_text = validate(g, inference="rdfs", abort_on_first=False)
    assert conforms, f"SHACL validation failed: {results_text}"
