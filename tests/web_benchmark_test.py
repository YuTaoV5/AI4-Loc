import importlib.util
import pathlib
import unittest

spec=importlib.util.spec_from_file_location('web_benchmark',pathlib.Path(__file__).parents[1]/'scripts/run-web-benchmark.py')
web=importlib.util.module_from_spec(spec);spec.loader.exec_module(web)

class WebBenchmarkTests(unittest.TestCase):
    def test_legacy_recipe_does_not_force_decision_service(self):
        control={'agent':{'model':'chat','baseUrl':'http://chat/v1'},'profile':{'agentId':'decision-chat','prompt':'User-selected instructions','skills':[{'id':'a','content':'Full body'}]},'decisionBaseUrl':'http://unused','decisionApi':'decisions'}
        request=web.agent_request(control,pathlib.Path('/anonymous'))
        self.assertNotIn('boundaryRouter',request)
        self.assertNotIn('decisionPlugin',request)
        self.assertEqual(request['skillSnapshots'],control['profile']['skills'])
