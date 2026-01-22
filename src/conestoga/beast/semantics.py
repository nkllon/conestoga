"""
Beast Semantic Alignment Layer

Provides semantic interoperability between Beast concepts and Eudorus ontology.
Maps Beast Agent, Task, and Validation entities to RDF/OWL representations.
"""

import logging
from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

# Define Beast semantics namespace
BEAST = Namespace("http://nkllon.com/ontology/beast#")
EUDORUS = Namespace("http://nkllon.com/ontology/eudorus#")


class SemanticAlignmentLayer:
    """
    Handles semantic alignment between Beast messaging and Eudorus ontology.

    Responsibilities:
    - Import and align with beast-semantics ontology
    - Map Agent, Task, and Validation entities
    - Support RDF/Turtle payload handling
    - Define observability monitoring classes
    """

    def __init__(self, ontology_path: str | None = None):
        """
        Initialize the semantic alignment layer.

        Args:
            ontology_path: Optional path to load existing ontology
        """
        self.graph = Graph()
        self._initialize_namespaces()
        self._define_core_classes()

        if ontology_path:
            self.load_ontology(ontology_path)

    def _initialize_namespaces(self):
        """Bind common namespaces to the graph."""
        self.graph.bind("beast", BEAST)
        self.graph.bind("eudorus", EUDORUS)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)

    def _define_core_classes(self):
        """Define core Beast and Eudorus ontology classes."""
        # Beast Agent class
        self.graph.add((BEAST.Agent, RDF.type, OWL.Class))
        self.graph.add((BEAST.Agent, RDFS.label, Literal("Beast Agent")))
        self.graph.add(
            (
                BEAST.Agent,
                RDFS.comment,
                Literal("An autonomous agent participating in the Beast network"),
            )
        )

        # Beast Task class
        self.graph.add((BEAST.Task, RDF.type, OWL.Class))
        self.graph.add((BEAST.Task, RDFS.label, Literal("Beast Task")))
        self.graph.add(
            (
                BEAST.Task,
                RDFS.comment,
                Literal("A unit of work assigned to or executed by an agent"),
            )
        )

        # Beast Validation class
        self.graph.add((BEAST.Validation, RDF.type, OWL.Class))
        self.graph.add((BEAST.Validation, RDFS.label, Literal("Beast Validation")))
        self.graph.add(
            (
                BEAST.Validation,
                RDFS.comment,
                Literal("A validation check or test result for a task or agent"),
            )
        )

        # Observability classes
        self.graph.add((EUDORUS.PrometheusExporter, RDF.type, OWL.Class))
        self.graph.add(
            (EUDORUS.PrometheusExporter, RDFS.label, Literal("Prometheus Exporter"))
        )
        self.graph.add(
            (
                EUDORUS.PrometheusExporter,
                RDFS.comment,
                Literal("Exports metrics in Prometheus format"),
            )
        )

        self.graph.add((EUDORUS.JaegerTracer, RDF.type, OWL.Class))
        self.graph.add((EUDORUS.JaegerTracer, RDFS.label, Literal("Jaeger Tracer")))
        self.graph.add(
            (
                EUDORUS.JaegerTracer,
                RDFS.comment,
                Literal("Distributed tracing component using Jaeger"),
            )
        )

        self.graph.add((EUDORUS.ObservatoryConnector, RDF.type, OWL.Class))
        self.graph.add(
            (EUDORUS.ObservatoryConnector, RDFS.label, Literal("Observatory Connector"))
        )
        self.graph.add(
            (
                EUDORUS.ObservatoryConnector,
                RDFS.comment,
                Literal("Connects agents to the Observatory monitoring system"),
            )
        )

        # Properties
        self.graph.add((BEAST.hasMonitor, RDF.type, OWL.ObjectProperty))
        self.graph.add((BEAST.hasMonitor, RDFS.domain, BEAST.Agent))
        self.graph.add((BEAST.hasMonitor, RDFS.range, EUDORUS.ObservatoryConnector))

        self.graph.add((BEAST.executesTask, RDF.type, OWL.ObjectProperty))
        self.graph.add((BEAST.executesTask, RDFS.domain, BEAST.Agent))
        self.graph.add((BEAST.executesTask, RDFS.range, BEAST.Task))

        self.graph.add((BEAST.hasValidation, RDF.type, OWL.ObjectProperty))
        self.graph.add((BEAST.hasValidation, RDFS.domain, BEAST.Task))
        self.graph.add((BEAST.hasValidation, RDFS.range, BEAST.Validation))

    def load_ontology(self, path: str, format: str = "turtle"):
        """
        Load an existing ontology file.

        Args:
            path: Path to the ontology file
            format: RDF format (turtle, xml, n3, etc.)
        """
        try:
            self.graph.parse(path, format=format)
            logging.info(f"Loaded ontology from {path}")
        except Exception as e:
            logging.error(f"Failed to load ontology from {path}: {e}")
            raise

    def save_ontology(self, path: str, format: str = "turtle"):
        """
        Save the current ontology to a file.

        Args:
            path: Path to save the ontology
            format: RDF format (turtle, xml, n3, etc.)
        """
        try:
            self.graph.serialize(destination=path, format=format)
            logging.info(f"Saved ontology to {path}")
        except Exception as e:
            logging.error(f"Failed to save ontology to {path}: {e}")
            raise

    def create_agent(
        self, agent_id: str, properties: dict[str, Any] | None = None
    ) -> URIRef:
        """
        Create an agent entity in the ontology.

        Args:
            agent_id: Unique identifier for the agent
            properties: Optional additional properties

        Returns:
            URIRef: The agent's URI reference
        """
        agent_uri = BEAST[f"agent/{agent_id}"]
        self.graph.add((agent_uri, RDF.type, BEAST.Agent))
        self.graph.add((agent_uri, RDFS.label, Literal(agent_id)))

        if properties:
            for key, value in properties.items():
                self.graph.add((agent_uri, BEAST[key], Literal(value)))

        logging.debug(f"Created agent entity: {agent_id}")
        return agent_uri

    def create_task(
        self,
        task_id: str,
        agent_uri: URIRef,
        properties: dict[str, Any] | None = None,
    ) -> URIRef:
        """
        Create a task entity in the ontology.

        Args:
            task_id: Unique identifier for the task
            agent_uri: URI of the agent executing the task
            properties: Optional additional properties

        Returns:
            URIRef: The task's URI reference
        """
        task_uri = BEAST[f"task/{task_id}"]
        self.graph.add((task_uri, RDF.type, BEAST.Task))
        self.graph.add((task_uri, RDFS.label, Literal(task_id)))
        self.graph.add((agent_uri, BEAST.executesTask, task_uri))

        if properties:
            for key, value in properties.items():
                self.graph.add((task_uri, BEAST[key], Literal(value)))

        logging.debug(f"Created task entity: {task_id} for agent {agent_uri}")
        return task_uri

    def create_validation(
        self,
        validation_id: str,
        task_uri: URIRef,
        result: bool,
        properties: dict[str, Any] | None = None,
    ) -> URIRef:
        """
        Create a validation entity in the ontology.

        Args:
            validation_id: Unique identifier for the validation
            task_uri: URI of the task being validated
            result: Validation result (pass/fail)
            properties: Optional additional properties

        Returns:
            URIRef: The validation's URI reference
        """
        validation_uri = BEAST[f"validation/{validation_id}"]
        self.graph.add((validation_uri, RDF.type, BEAST.Validation))
        self.graph.add((validation_uri, RDFS.label, Literal(validation_id)))
        self.graph.add((task_uri, BEAST.hasValidation, validation_uri))
        self.graph.add((validation_uri, BEAST.result, Literal(result)))

        if properties:
            for key, value in properties.items():
                self.graph.add((validation_uri, BEAST[key], Literal(value)))

        logging.debug(f"Created validation entity: {validation_id} for task {task_uri}")
        return validation_uri

    def link_agent_to_monitor(self, agent_uri: URIRef, monitor_type: str) -> URIRef:
        """
        Link an agent to a monitoring component.

        Args:
            agent_uri: URI of the agent
            monitor_type: Type of monitor (prometheus, jaeger, observatory)

        Returns:
            URIRef: The monitor's URI reference
        """
        monitor_class_map = {
            "prometheus": EUDORUS.PrometheusExporter,
            "jaeger": EUDORUS.JaegerTracer,
            "observatory": EUDORUS.ObservatoryConnector,
        }

        monitor_class = monitor_class_map.get(monitor_type.lower())
        if not monitor_class:
            raise ValueError(f"Unknown monitor type: {monitor_type}")

        monitor_uri = EUDORUS[f"monitor/{monitor_type}/{agent_uri.split('/')[-1]}"]
        self.graph.add((monitor_uri, RDF.type, monitor_class))
        self.graph.add((agent_uri, BEAST.hasMonitor, monitor_uri))

        logging.debug(f"Linked agent {agent_uri} to {monitor_type} monitor")
        return monitor_uri

    def process_rdf_payload(self, rdf_content: str, format: str = "turtle") -> int:
        """
        Process an RDF/Turtle payload and merge it into the knowledge graph.

        Args:
            rdf_content: RDF content as string
            format: RDF format (turtle, xml, n3, etc.)

        Returns:
            int: Number of triples added
        """
        initial_size = len(self.graph)

        try:
            self.graph.parse(data=rdf_content, format=format)
            triples_added = len(self.graph) - initial_size
            logging.info(f"Processed RDF payload: {triples_added} triples added")
            return triples_added
        except Exception as e:
            logging.error(f"Failed to process RDF payload: {e}")
            raise

    def export_as_turtle(self) -> str:
        """
        Export the current knowledge graph as Turtle format.

        Returns:
            str: RDF graph serialized as Turtle
        """
        return self.graph.serialize(format="turtle")

    def query_agents(self) -> list[str]:
        """
        Query all agents in the knowledge graph.

        Returns:
            List[str]: List of agent IDs
        """
        query = """
        SELECT ?agent ?label
        WHERE {
            ?agent rdf:type beast:Agent .
            ?agent rdfs:label ?label .
        }
        """
        results = self.graph.query(query)
        agents = []
        for row in results:
            if hasattr(row, "label"):
                agents.append(str(row.label))
        return agents

    def query_agent_tasks(self, agent_id: str) -> list[str]:
        """
        Query all tasks for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List[str]: List of task IDs
        """
        agent_uri = BEAST[f"agent/{agent_id}"]
        query = f"""
        SELECT ?task ?label
        WHERE {{
            <{agent_uri}> beast:executesTask ?task .
            ?task rdfs:label ?label .
        }}
        """
        results = self.graph.query(query)
        tasks = []
        for row in results:
            if hasattr(row, "label"):
                tasks.append(str(row.label))
        return tasks
