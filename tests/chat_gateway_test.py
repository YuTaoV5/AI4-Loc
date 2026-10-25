import contextlib
import http.client
import importlib.util
import io
import json
import pathlib
import threading
import unittest
import unittest.mock
import urllib.error

spec=importlib.util.spec_from_file_location('chat_gateway',pathlib.Path(__file__).parents[1]/'scripts/chat-gateway.py')
gateway=importlib.util.module_from_spec(spec);spec.loader.exec_module(gateway)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.config={'model':'MiniMax-M2.7','baseUrl':'https://api.minimax.cn/v1','apiKey':'fake-server-only-key'}
        self.server=gateway.http.server.ThreadingHTTPServer(('127.0.0.1',0),gateway.handler(self.config))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)

    def request(self,path,body=None):
        client=http.client.HTTPConnection(*self.server.server_address,timeout=5)
        client.request('POST' if body else 'GET',path,json.dumps(body) if body else None,{'Content-Type':'application/json'})
        response=client.getresponse();status=response.status;raw=response.read();client.close()
        return status,raw

    def test_model_discovery_never_returns_credential(self):
        status,raw=self.request('/v1/models')
        self.assertEqual(status,200);self.assertIn(b'MiniMax-M2.7',raw)
        self.assertNotIn(self.config['apiKey'].encode(),raw)

    def test_tool_history_and_stream_are_forwarded_without_changes(self):
        payload={'model':'MiniMax-M2.7','stream':True,'messages':[{'role':'assistant','content':'<think>context</think>','tool_calls':[{'id':'one'}]}]}
        raw=b'data: {"choices":[{"delta":{"content":"report"}}]}\n\ndata: [DONE]\n\n'
        upstream=io.BytesIO(raw);upstream.status=200;upstream.headers={'Content-Type':'text/event-stream'}
        with unittest.mock.patch.object(gateway.urllib.request,'urlopen',return_value=upstream) as call:
            status,body=self.request('/v1/chat/completions',payload)
        request=call.call_args.args[0]
        self.assertEqual(json.loads(request.data),payload)
        self.assertEqual(request.get_header('Authorization'),'Bearer fake-server-only-key')
        self.assertEqual(status,200);self.assertEqual(body,raw)

    def test_wrong_model_is_rejected_before_provider_call(self):
        with unittest.mock.patch.object(gateway.urllib.request,'urlopen') as call:
            self.assertEqual(self.request('/v1/chat/completions',{'model':'other'})[0],400)
        call.assert_not_called()

    def test_provider_error_does_not_disclose_credential(self):
        error=urllib.error.HTTPError('https://api.minimax.cn',401,'Unauthorized',{},io.BytesIO(self.config['apiKey'].encode()))
        with unittest.mock.patch.object(gateway.urllib.request,'urlopen',side_effect=error):
            status,raw=self.request('/v1/chat/completions',{'model':'MiniMax-M2.7'})
        self.assertEqual(status,401);self.assertNotIn(self.config['apiKey'].encode(),raw)

    def test_missing_done_is_added_only_after_terminal_frame(self):
        terminal=b'data: {"choices":[{"finish_reason":"tool_calls","delta":{}}]}\n\n'
        upstream=io.BytesIO(terminal);upstream.status=200;upstream.headers={'Content-Type':'text/event-stream'}
        with unittest.mock.patch.object(gateway.urllib.request,'urlopen',return_value=upstream):
            status,raw=self.request('/v1/chat/completions',{'model':'MiniMax-M2.7','stream':True})
        self.assertEqual(status,200);self.assertEqual(raw.count(b'[DONE]'),1)

    def test_truncated_stream_cannot_be_converted_to_success(self):
        partial=b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        upstream=io.BytesIO(partial);upstream.status=200;upstream.headers={'Content-Type':'text/event-stream'}
        with unittest.mock.patch.object(gateway.urllib.request,'urlopen',return_value=upstream):
            status,raw=self.request('/v1/chat/completions',{'model':'MiniMax-M2.7','stream':True})
        self.assertEqual(status,200);self.assertEqual(raw,partial)
