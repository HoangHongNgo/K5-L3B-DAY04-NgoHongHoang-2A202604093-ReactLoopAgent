"""Kiểm tra phục hồi lỗi và trace của CP3, không gọi API thật."""
import json
import unittest
from unittest.mock import Mock

from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class ErrorHandlingTests(unittest.TestCase):
    def test_tool_exception_does_not_skip_other_calls(self):
        first = tool_call('a', 'get_status', '{"provider":"github"}')
        second = tool_call('b', 'get_status', '{"provider":"cloudflare"}')
        first['calls'] += second['calls']
        first['message']['tool_calls'] += second['message']['tool_calls']
        tools = Mock()
        tools.execute.side_effect = [TimeoutError('timed out'), {'ok': True}]
        provider = FakeProvider([first, final()])
        result = run_agent('check', provider, tools)
        self.assertEqual(result['status'], 'completed')
        history = provider.histories[1]
        self.assertIs(history[-3], first['message'])
        self.assertEqual([m['tool_call_id'] for m in history[-2:]], ['a', 'b'])
        self.assertEqual(json.loads(history[-2]['content'])['error'], 'TimeoutError')
        events = [e for e in result['trace'] if e['event'] == 'tool']
        self.assertEqual(events[0]['arguments'], {'provider': 'github'})
        self.assertTrue(events[1]['result']['ok'])

    def test_execution_value_error_is_not_invalid_json(self):
        tools = Mock()
        tools.execute.side_effect = ValueError('invalid provider')
        provider = FakeProvider([tool_call('a', 'get_status', '{}'), final()])
        result = run_agent('check', provider, tools)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(json.loads(provider.histories[1][-1]['content'])['error'], 'ValueError')

    def test_invalid_arguments_are_observations(self):
        for args in ('{', '[]', 'null', '42'):
            with self.subTest(args=args):
                tools = Mock()
                provider = FakeProvider([tool_call('a', 'get_status', args), final()])
                result = run_agent('check', provider, tools)
                tools.execute.assert_not_called()
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(json.loads(provider.histories[1][-1]['content'])['error'], 'INVALID_ARGUMENTS')

    def test_registry_errors_are_returned_to_model(self):
        cases = [('missing', '{}', 'UNKNOWN_TOOL'),
                 ('get_status', '{"provider":"invalid"}', 'ValueError')]
        for name, args, error in cases:
            with self.subTest(name=name):
                provider = FakeProvider([tool_call('a', name, args), final()])
                result = run_agent('check', provider, StatusTools())
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(json.loads(provider.histories[1][-1]['content'])['error'], error)

    def test_provider_failure_preserves_prior_trace_and_usage(self):
        response = tool_call('a', 'get_status', '{"provider":"github"}')
        response['usage'] = {'total_tokens': 10}
        provider = Mock()
        provider.complete.side_effect = [response, RuntimeError('provider unavailable')]
        result = run_agent('check', provider, StatusTools())
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['answer'], '')
        self.assertEqual(result['usage'], [{'total_tokens': 10}])
        self.assertEqual(result['trace'][-1]['error'], 'PROVIDER_ERROR')
        self.assertEqual(result['trace'][-1]['step'], 2)

    def test_truncated_tool_call_is_not_executed(self):
        response = tool_call('a', 'get_status', '{')
        response['finish'] = 'length'
        tools = Mock()
        result = run_agent('check', FakeProvider([response]), tools)
        tools.execute.assert_not_called()
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['trace'][-1]['error'], 'OUTPUT_TRUNCATED')

    def test_unexpected_finish_is_error(self):
        for finish in ('content_filter', None, 'tool_calls'):
            with self.subTest(finish=finish):
                response = final('partial')
                response['finish'] = finish
                result = run_agent('check', FakeProvider([response]), StatusTools())
                self.assertEqual(result['status'], 'error')
                self.assertEqual(result['trace'][-1]['error'], 'UNEXPECTED_FINISH')

    def test_budget_limits_model_calls(self):
        provider = FakeProvider([tool_call('a', 'get_status', '{"provider":"github"}')])
        result = run_agent('check', provider, StatusTools(), max_steps=1)
        self.assertEqual(result['status'], 'max_steps')
        self.assertEqual(len(provider.histories), 1)
        self.assertEqual(result['trace'][-1], {'event': 'max_steps', 'step': 1})
