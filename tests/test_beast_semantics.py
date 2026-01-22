"""Tests for Beast semantic alignment and ontology operations"""
import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from conestoga.beast.semantics import (
    SemanticAlignmentLayer,
    BEAST,
    EUDORUS,
)


class TestSemanticAlignmentLayerInit:
    """Test semantic alignment layer initialization"""

    def test_init_basic(self):
        """Test basic initialization"""
        layer = SemanticAlignmentLayer()

        assert isinstance(layer.graph, Graph)
        assert len(layer.graph) > 0  # Should have core classes defined

    def test_init_with_ontology_path(self, tmp_path):
        """Test initialization with ontology file"""
        # Create a simple test ontology
        test_ontology = tmp_path / "test.ttl"
        test_graph = Graph()
        test_graph.bind("beast", BEAST)
        test_uri = BEAST["test/entity"]
        test_graph.add((test_uri, RDF.type, BEAST.Agent))
        test_graph.serialize(destination=str(test_ontology), format="turtle")

        # Load it
        layer = SemanticAlignmentLayer(ontology_path=str(test_ontology))

        # Should contain the test entity
        assert (test_uri, RDF.type, BEAST.Agent) in layer.graph

    def test_namespaces_bound(self):
        """Test that namespaces are properly bound"""
        layer = SemanticAlignmentLayer()

        # Check namespace bindings
        namespaces = {ns: uri for ns, uri in layer.graph.namespaces()}
        assert "beast" in namespaces
        assert "eudorus" in namespaces
        assert "rdf" in namespaces
        assert "rdfs" in namespaces
        assert "owl" in namespaces


class TestSemanticAlignmentLayerCoreClasses:
    """Test core ontology class definitions"""

    def test_beast_agent_class_defined(self):
        """Test that Beast Agent class is defined"""
        layer = SemanticAlignmentLayer()

        # Check Agent class exists
        assert (BEAST.Agent, RDF.type, None) in layer.graph

    def test_beast_task_class_defined(self):
        """Test that Beast Task class is defined"""
        layer = SemanticAlignmentLayer()

        # Check Task class exists
        assert (BEAST.Task, RDF.type, None) in layer.graph

    def test_beast_validation_class_defined(self):
        """Test that Beast Validation class is defined"""
        layer = SemanticAlignmentLayer()

        # Check Validation class exists
        assert (BEAST.Validation, RDF.type, None) in layer.graph

    def test_observability_classes_defined(self):
        """Test that observability classes are defined"""
        layer = SemanticAlignmentLayer()

        # Check observability classes
        assert (EUDORUS.PrometheusExporter, RDF.type, None) in layer.graph
        assert (EUDORUS.JaegerTracer, RDF.type, None) in layer.graph
        assert (EUDORUS.ObservatoryConnector, RDF.type, None) in layer.graph

    def test_properties_defined(self):
        """Test that ontology properties are defined"""
        layer = SemanticAlignmentLayer()

        # Check properties exist
        assert (BEAST.hasMonitor, RDF.type, None) in layer.graph
        assert (BEAST.executesTask, RDF.type, None) in layer.graph
        assert (BEAST.hasValidation, RDF.type, None) in layer.graph


class TestSemanticAlignmentLayerAgentOperations:
    """Test agent creation and operations"""

    def test_create_agent_basic(self):
        """Test creating a basic agent"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent-1")

        # Verify agent was created
        assert isinstance(agent_uri, URIRef)
        assert (agent_uri, RDF.type, BEAST.Agent) in layer.graph
        assert (agent_uri, RDFS.label, Literal("test-agent-1")) in layer.graph

    def test_create_agent_with_properties(self):
        """Test creating agent with additional properties"""
        layer = SemanticAlignmentLayer()

        properties = {"role": "coordinator", "status": "active"}
        agent_uri = layer.create_agent(agent_id="test-agent-2", properties=properties)

        # Verify properties were added
        assert (agent_uri, BEAST["role"], Literal("coordinator")) in layer.graph
        assert (agent_uri, BEAST["status"], Literal("active")) in layer.graph

    def test_create_multiple_agents(self):
        """Test creating multiple agents"""
        layer = SemanticAlignmentLayer()

        agent1 = layer.create_agent(agent_id="agent-1")
        agent2 = layer.create_agent(agent_id="agent-2")

        # Both should exist
        assert (agent1, RDF.type, BEAST.Agent) in layer.graph
        assert (agent2, RDF.type, BEAST.Agent) in layer.graph

        # Should be different URIs
        assert agent1 != agent2

    def test_query_agents(self):
        """Test querying all agents"""
        layer = SemanticAlignmentLayer()

        # Create some agents
        layer.create_agent(agent_id="agent-1")
        layer.create_agent(agent_id="agent-2")
        layer.create_agent(agent_id="agent-3")

        # Query agents
        agents = layer.query_agents()

        assert len(agents) >= 3
        assert "agent-1" in agents
        assert "agent-2" in agents
        assert "agent-3" in agents


class TestSemanticAlignmentLayerTaskOperations:
    """Test task creation and operations"""

    def test_create_task_basic(self):
        """Test creating a basic task"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        task_uri = layer.create_task(task_id="test-task", agent_uri=agent_uri)

        # Verify task was created
        assert isinstance(task_uri, URIRef)
        assert (task_uri, RDF.type, BEAST.Task) in layer.graph
        assert (task_uri, RDFS.label, Literal("test-task")) in layer.graph

        # Verify task is linked to agent
        assert (agent_uri, BEAST.executesTask, task_uri) in layer.graph

    def test_create_task_with_properties(self):
        """Test creating task with additional properties"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        properties = {"status": "running", "priority": "high"}
        task_uri = layer.create_task(
            task_id="test-task", agent_uri=agent_uri, properties=properties
        )

        # Verify properties were added
        assert (task_uri, BEAST["status"], Literal("running")) in layer.graph
        assert (task_uri, BEAST["priority"], Literal("high")) in layer.graph

    def test_create_multiple_tasks_for_agent(self):
        """Test creating multiple tasks for same agent"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        task1 = layer.create_task(task_id="task-1", agent_uri=agent_uri)
        task2 = layer.create_task(task_id="task-2", agent_uri=agent_uri)

        # Both tasks should be linked to agent
        assert (agent_uri, BEAST.executesTask, task1) in layer.graph
        assert (agent_uri, BEAST.executesTask, task2) in layer.graph

    def test_query_agent_tasks(self):
        """Test querying tasks for specific agent"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        layer.create_task(task_id="task-1", agent_uri=agent_uri)
        layer.create_task(task_id="task-2", agent_uri=agent_uri)

        # Create another agent with a task
        other_agent = layer.create_agent(agent_id="other-agent")
        layer.create_task(task_id="other-task", agent_uri=other_agent)

        # Query tasks for test-agent
        tasks = layer.query_agent_tasks("test-agent")

        assert len(tasks) == 2
        assert "task-1" in tasks
        assert "task-2" in tasks
        assert "other-task" not in tasks


class TestSemanticAlignmentLayerValidationOperations:
    """Test validation creation and operations"""

    def test_create_validation_basic(self):
        """Test creating a basic validation"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        task_uri = layer.create_task(task_id="test-task", agent_uri=agent_uri)
        validation_uri = layer.create_validation(
            validation_id="test-validation", task_uri=task_uri, result=True
        )

        # Verify validation was created
        assert isinstance(validation_uri, URIRef)
        assert (validation_uri, RDF.type, BEAST.Validation) in layer.graph
        assert (validation_uri, RDFS.label, Literal("test-validation")) in layer.graph
        assert (validation_uri, BEAST.result, Literal(True)) in layer.graph

        # Verify validation is linked to task
        assert (task_uri, BEAST.hasValidation, validation_uri) in layer.graph

    def test_create_validation_with_properties(self):
        """Test creating validation with additional properties"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        task_uri = layer.create_task(task_id="test-task", agent_uri=agent_uri)
        properties = {"checker": "automated", "timestamp": "2024-01-01"}
        validation_uri = layer.create_validation(
            validation_id="test-validation",
            task_uri=task_uri,
            result=False,
            properties=properties,
        )

        # Verify properties were added
        assert (validation_uri, BEAST["checker"], Literal("automated")) in layer.graph
        assert (validation_uri, BEAST["timestamp"], Literal("2024-01-01")) in layer.graph
        assert (validation_uri, BEAST.result, Literal(False)) in layer.graph

    def test_create_multiple_validations_for_task(self):
        """Test creating multiple validations for same task"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        task_uri = layer.create_task(task_id="test-task", agent_uri=agent_uri)
        val1 = layer.create_validation(
            validation_id="validation-1", task_uri=task_uri, result=True
        )
        val2 = layer.create_validation(
            validation_id="validation-2", task_uri=task_uri, result=False
        )

        # Both validations should be linked to task
        assert (task_uri, BEAST.hasValidation, val1) in layer.graph
        assert (task_uri, BEAST.hasValidation, val2) in layer.graph


class TestSemanticAlignmentLayerMonitorOperations:
    """Test monitor linking operations"""

    def test_link_agent_to_prometheus(self):
        """Test linking agent to Prometheus monitor"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        monitor_uri = layer.link_agent_to_monitor(agent_uri, "prometheus")

        # Verify monitor was created and linked
        assert isinstance(monitor_uri, URIRef)
        assert (monitor_uri, RDF.type, EUDORUS.PrometheusExporter) in layer.graph
        assert (agent_uri, BEAST.hasMonitor, monitor_uri) in layer.graph

    def test_link_agent_to_jaeger(self):
        """Test linking agent to Jaeger monitor"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        monitor_uri = layer.link_agent_to_monitor(agent_uri, "jaeger")

        assert (monitor_uri, RDF.type, EUDORUS.JaegerTracer) in layer.graph
        assert (agent_uri, BEAST.hasMonitor, monitor_uri) in layer.graph

    def test_link_agent_to_observatory(self):
        """Test linking agent to Observatory monitor"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        monitor_uri = layer.link_agent_to_monitor(agent_uri, "observatory")

        assert (monitor_uri, RDF.type, EUDORUS.ObservatoryConnector) in layer.graph
        assert (agent_uri, BEAST.hasMonitor, monitor_uri) in layer.graph

    def test_link_agent_to_invalid_monitor(self):
        """Test linking to invalid monitor type raises error"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")

        with pytest.raises(ValueError, match="Unknown monitor type"):
            layer.link_agent_to_monitor(agent_uri, "invalid_monitor")

    def test_link_agent_to_multiple_monitors(self):
        """Test linking agent to multiple monitors"""
        layer = SemanticAlignmentLayer()

        agent_uri = layer.create_agent(agent_id="test-agent")
        prometheus_uri = layer.link_agent_to_monitor(agent_uri, "prometheus")
        jaeger_uri = layer.link_agent_to_monitor(agent_uri, "jaeger")

        # Both monitors should be linked
        assert (agent_uri, BEAST.hasMonitor, prometheus_uri) in layer.graph
        assert (agent_uri, BEAST.hasMonitor, jaeger_uri) in layer.graph


class TestSemanticAlignmentLayerRDFOperations:
    """Test RDF/Turtle payload processing"""

    def test_process_rdf_payload_turtle(self):
        """Test processing RDF payload in Turtle format"""
        layer = SemanticAlignmentLayer()

        rdf_content = """
@prefix beast: <http://nkllon.com/ontology/beast#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://nkllon.com/ontology/beast#agent/imported-agent> a beast:Agent ;
    rdfs:label "Imported Agent" .
"""

        initial_size = len(layer.graph)
        triples_added = layer.process_rdf_payload(rdf_content, format="turtle")

        # Verify triples were added
        assert triples_added > 0
        assert len(layer.graph) > initial_size

        # Verify the imported agent exists
        imported_uri = BEAST["agent/imported-agent"]
        assert (imported_uri, RDF.type, BEAST.Agent) in layer.graph

    def test_process_rdf_payload_invalid(self):
        """Test processing invalid RDF raises error"""
        layer = SemanticAlignmentLayer()

        invalid_rdf = "this is not valid RDF"

        with pytest.raises(Exception):
            layer.process_rdf_payload(invalid_rdf, format="turtle")

    def test_export_as_turtle(self):
        """Test exporting graph as Turtle format"""
        layer = SemanticAlignmentLayer()

        # Create some entities
        layer.create_agent(agent_id="export-test-agent")

        # Export as Turtle
        turtle_output = layer.export_as_turtle()

        # Verify it's a string
        assert isinstance(turtle_output, str)

        # Verify it contains our agent
        assert "export-test-agent" in turtle_output


class TestSemanticAlignmentLayerPersistence:
    """Test ontology loading and saving"""

    def test_save_ontology(self, tmp_path):
        """Test saving ontology to file"""
        layer = SemanticAlignmentLayer()

        # Create some entities
        layer.create_agent(agent_id="save-test-agent")

        # Save to file
        save_path = tmp_path / "test_ontology.ttl"
        layer.save_ontology(str(save_path), format="turtle")

        # Verify file was created
        assert save_path.exists()

        # Verify it can be loaded
        loaded_graph = Graph()
        loaded_graph.parse(str(save_path), format="turtle")
        assert len(loaded_graph) > 0

    def test_load_ontology(self, tmp_path):
        """Test loading ontology from file"""
        # Create and save an ontology
        layer1 = SemanticAlignmentLayer()
        agent_uri = layer1.create_agent(agent_id="load-test-agent")
        save_path = tmp_path / "test_ontology.ttl"
        layer1.save_ontology(str(save_path), format="turtle")

        # Load it in a new layer
        layer2 = SemanticAlignmentLayer(ontology_path=str(save_path))

        # Verify the agent exists in the loaded graph
        assert (agent_uri, RDF.type, BEAST.Agent) in layer2.graph

    def test_ontology_roundtrip(self, tmp_path):
        """Test saving and loading preserves ontology"""
        # Create ontology with various entities
        layer1 = SemanticAlignmentLayer()
        agent_uri = layer1.create_agent(agent_id="roundtrip-agent")
        task_uri = layer1.create_task(task_id="roundtrip-task", agent_uri=agent_uri)
        val_uri = layer1.create_validation(
            validation_id="roundtrip-validation", task_uri=task_uri, result=True
        )

        # Save and load
        save_path = tmp_path / "roundtrip.ttl"
        layer1.save_ontology(str(save_path))
        layer2 = SemanticAlignmentLayer(ontology_path=str(save_path))

        # Verify all entities exist
        assert (agent_uri, RDF.type, BEAST.Agent) in layer2.graph
        assert (task_uri, RDF.type, BEAST.Task) in layer2.graph
        assert (val_uri, RDF.type, BEAST.Validation) in layer2.graph
        assert (agent_uri, BEAST.executesTask, task_uri) in layer2.graph
        assert (task_uri, BEAST.hasValidation, val_uri) in layer2.graph
