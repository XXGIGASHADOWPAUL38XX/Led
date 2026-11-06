import json
import unittest
from copy import deepcopy
from unittest.mock import patch


from ai.template_generator.agent import NodeCatalog
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = NodeCatalog()
        self.source = {"nodes": [], "connects": []}
        self.catalog.begin(self.source)

    def add(self, node_type, configure=None, wire=None):
        questions, resolve = self.catalog.prepare_add(node_type)
        answers = {key: {"choice": "original"} for key in questions}
        if configure:
            configure(questions, answers)
        state = resolve(answers)
        questions, resolve = self.catalog.prepare_wiring(state)
        answers = {key: {"choice": "none"} for key in questions}
        if wire:
            wire(questions, answers)
        self.catalog.accept(resolve(answers))

    def test_more_than_eight_instances_and_evolving_context(self):
        self.assertNotIn("finish", self.catalog.questions()["next_node"]["criteria"])
        for _ in range(9):
            self.add("ConstantArray")
        context = json.loads(self.catalog.context("nine constant arrays"))
        self.assertEqual(len(context["current_graph"]["nodes"]), 9)
        self.assertIn("Buffer", context["catalog"])
        self.assertNotIn("finish", self.catalog.questions()["next_node"]["criteria"])
        self.assertEqual(self.source, {"nodes": [], "connects": []})

    def test_festival_source_and_fixed_chart(self):
        import inspect
        import numpy as np
        self.assertEqual(set(self.catalog.questions()["next_node"]["criteria"]), {"SCPlaylistPlayer"})
        self.source["nodes"] = [{"class": "SCPlaylistPlayer", "state": {
            "ctor_kwargs": {"playlist_url": "https://soundcloud.com/other/sets/custom"}}}]
        self.add("SCPlaylistPlayer")
        player = self.catalog.selected[0]
        default_url = inspect.signature(type(player)).parameters["playlist_url"].default
        self.assertEqual(player.playlist_url.value, default_url)
        self.assertNotIn("BarGraphChart", self.catalog.questions()["next_node"]["criteria"])
        self.add("RGBAPipeline")
        self.assertIn("BarGraphChart", self.catalog.questions()["next_node"]["criteria"])
        questions, resolve = self.catalog.prepare_add("BarGraphChart")
        self.assertEqual(questions, {})
        questions, resolve = self.catalog.prepare_wiring(resolve({}))
        self.assertEqual(len(questions), 1)
        question = next(iter(questions.values()))
        self.assertNotIn("none", question["criteria"])
        self.assertIn(".brushes", question["instructions"])
        self.catalog.accept(resolve({key: {"choice": next(iter(question["criteria"]))}
                                     for key, question in questions.items()}))
        chart = self.catalog.selected[-1]
        self.assertEqual(chart.number_points.value, 180)
        np.testing.assert_array_equal(chart.data.value, np.ones(180))
        self.assertEqual(set(self.catalog.questions()["next_node"]["criteria"]), {"finish"})
        self.assertIs(self.catalog.complete(), self.catalog.state)
        self.catalog.state["nodes"][-1]["state"]["ctor_kwargs"]["number_points"] = 179
        with self.assertRaisesRegex(ValueError, "180-bar"):
            self.catalog.complete()

    def test_wiring_and_registry_isolation(self):
        audio, visual = list(audio_updatable_objects), list(visual_updatable_objects)
        self.add("ConstantArray")

        def wire(questions, answers):
            key = next(iter(questions))
            source = next(name for name, description in questions[key]["criteria"].items()
                          if description.startswith("ConstantArray.0.data:"))
            answers[key] = {"choice": source}

        self.add("Clip", wire=wire)
        self.assertEqual(self.catalog.state["connects"], [("ConstantArray.0", "data", "Clip.0", "input_value")])
        self.assertEqual(audio_updatable_objects, audio)
        self.assertEqual(visual_updatable_objects, visual)

    def test_operator_argument_references_create_connections(self):
        self.add("ConstantArray")

        def configure(questions, answers):
            key = next(key for key, question in questions.items()
                       if question["instructions"].startswith("Choose OperatorPipeline.0.arguments.source."))
            choice = next(name for name in questions[key]["criteria"] if name.startswith("source_ConstantArray.0_data"))
            answers[key] = {"choice": choice}

        self.add("OperatorPipeline", configure=configure)
        self.assertEqual(len(self.catalog.state["connects"]), 1)
        self.assertEqual(self.catalog.state["nodes"][-1]["state"]["ctor_kwargs"]["length"], self.catalog.selected[0].data.value.size)

    def test_saved_graph_loads_through_headless_runtime(self):
        from backend.api.runtime import Runtime
        self.add("ConstantArray")
        self.add("Clip", wire=lambda questions, answers: answers.update(
            {key: {"choice": "source_1"} for key in questions}))
        runtime = Runtime()
        try:
            runtime.load_template(json.loads(json.dumps(self.catalog.state)))
            self.assertIn("Clip.0", runtime.nodes)
            self.assertIs(runtime.nodes["Clip.0"].input_value._value_source,
                          runtime.nodes["ConstantArray.0"].data)
            self.assertEqual(runtime.tick(), [])
        finally:
            runtime.close()

    def test_invalid_graph_and_iteration_limit(self):
        self.add("ConstantArray")
        state = deepcopy(self.catalog.state)
        state["nodes"].append(deepcopy(state["nodes"][0]))
        with self.assertRaisesRegex(ValueError, "uniquely named"):
            self.catalog.validate(state)
        state = deepcopy(self.catalog.state)
        state["nodes"][0]["state"]["init_refs"] = {
            "input_value": {"__element_ref__": {"node_name": "missing", "element_name": "data"}}}
        with self.assertRaisesRegex(ValueError, "Unknown reference"):
            self.catalog.validate(state)
        with patch.dict("os.environ", {"JEV_MAX_STEPS": "1"}):
            with self.assertRaisesRegex(ValueError, "JEV_MAX_STEPS"):
                self.catalog.questions()


if __name__ == "__main__":
    unittest.main()
