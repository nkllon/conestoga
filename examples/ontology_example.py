"""
Example: RDF/OWL Ontology Management

This example demonstrates how to work with RDF graphs and OWL ontologies.
"""

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL
from owlrl import DeductiveClosure, RDFS_Semantics
from dotenv import load_dotenv


def create_sample_ontology():
    """Create a sample ontology with classes and properties."""
    g = Graph()
    
    # Define custom namespace
    EX = Namespace("http://example.org/ontology#")
    g.bind("ex", EX)
    g.bind("owl", OWL)
    
    # Define classes
    g.add((EX.Animal, RDF.type, OWL.Class))
    g.add((EX.Mammal, RDF.type, OWL.Class))
    g.add((EX.Dog, RDF.type, OWL.Class))
    
    # Define class hierarchy
    g.add((EX.Mammal, RDFS.subClassOf, EX.Animal))
    g.add((EX.Dog, RDFS.subClassOf, EX.Mammal))
    
    # Define properties
    g.add((EX.hasName, RDF.type, OWL.DatatypeProperty))
    g.add((EX.hasOwner, RDF.type, OWL.ObjectProperty))
    
    # Add instances
    g.add((EX.Buddy, RDF.type, EX.Dog))
    g.add((EX.Buddy, EX.hasName, Literal("Buddy")))
    
    print(f"✅ Created sample ontology with {len(g)} triples")
    return g


def apply_reasoning(g: Graph):
    """Apply RDFS reasoning to infer new triples."""
    print("\n🧠 Applying RDFS reasoning...")
    
    # Get initial count
    initial_count = len(g)
    
    # Apply RDFS reasoning
    DeductiveClosure(RDFS_Semantics).expand(g)
    
    # Get new count
    final_count = len(g)
    inferred = final_count - initial_count
    
    print(f"✅ Inferred {inferred} new triples")
    print(f"   Total triples: {final_count}")
    
    return g


def query_ontology(g: Graph):
    """Query the ontology using SPARQL."""
    print("\n🔍 Querying ontology...")
    
    # Query for all classes
    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    
    SELECT ?class WHERE {
        ?class rdf:type owl:Class .
    }
    """
    
    print("  Classes in ontology:")
    for row in g.query(query):
        class_uri = str(row[0]).split('#')[-1]
        print(f"    - {class_uri}")
    
    # Query for instances and their types
    instance_query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX ex: <http://example.org/ontology#>
    
    SELECT ?instance ?type WHERE {
        ?instance rdf:type ?type .
        FILTER(STRSTARTS(STR(?instance), "http://example.org/ontology#"))
        FILTER(?type != <http://www.w3.org/2002/07/owl#NamedIndividual>)
    }
    """
    
    print("\n  Instances and their types:")
    for row in g.query(instance_query):
        inst = str(row[0]).split('#')[-1]
        typ = str(row[1]).split('#')[-1]
        print(f"    - {inst} is a {typ}")


def serialize_ontology(g: Graph, format="turtle"):
    """Serialize the ontology to different formats."""
    print(f"\n📄 Serializing ontology to {format} format...")
    
    serialized = g.serialize(format=format)
    print("Sample output (first 500 chars):")
    print(serialized[:500])
    
    return serialized


def main():
    """Main demonstration function."""
    load_dotenv()
    
    print("🦉 RDF/OWL Ontology Management Example")
    print("=" * 50)
    
    # Create ontology
    g = create_sample_ontology()
    
    # Apply reasoning
    g = apply_reasoning(g)
    
    # Query ontology
    query_ontology(g)
    
    # Serialize
    serialize_ontology(g)
    
    print("\n✅ Ontology management demonstration complete!")


if __name__ == "__main__":
    main()
