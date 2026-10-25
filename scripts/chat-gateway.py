"""Loopback Chat gateway: keep provider credentials outside Agent workspaces."""
import argparse
import http.server
import json
import pathlib
import urllib.error
import urllib.request


class StreamEnd:
    """MiniMax may omit [DONE]; append it only after a real terminal finish frame."""
    def __init__(self):
        self.buffer=b'';self.done=False;self.finished=False

    def feed(self,chunk):
        self.buffer+=chunk
        while b'\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\n',1)
            if not line.startswith(b'data:'):
                continue
            data=line[5:].strip()
            if data==b'[DONE]':
                self.done=True
                continue
            try:
                event=json.loads(data)
                if event.get('error'):
                    self.finished=False
                elif any(c.get('finish_reason') in ('stop','tool_calls','length','content_filter') for c in event.get('choices',[])):
                    self.finished=True
            except ValueError:
                pass
        if len(self.buffer)>8*1024*1024:
            raise ValueError('Oversized SSE frame')


def handler(config):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def json_response(self, status, value):
            raw=json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path!='/v1/models':
                return self.json_response(404,{'error':'Unknown endpoint'})
            self.json_response(200,{'object':'list','data':[{'id':config['model'],'object':'model','owned_by':'minimax'}]})

        def do_POST(self):
            if self.path!='/v1/chat/completions':
                return self.json_response(404,{'error':'Unknown endpoint'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=8*1024*1024:
                    return self.json_response(413,{'error':'Request exceeds size limit'})
                payload=json.loads(self.rfile.read(size))
                if payload.get('model')!=config['model']:
                    return self.json_response(400,{'error':'Model is not configured'})
                request=urllib.request.Request(
                    config['baseUrl'].rstrip('/')+'/chat/completions',
                    data=json.dumps(payload).encode(),
                    headers={'Content-Type':'application/json','Authorization':'Bearer '+config['apiKey']})
                with urllib.request.urlopen(request,timeout=300) as response:
                    self.send_response(response.status)
                    self.send_header('Content-Type',response.headers.get('Content-Type','application/json'))
                    self.send_header('Connection','close')
                    self.end_headers()
                    self.close_connection=True
                    stream=StreamEnd() if payload.get('stream') else None
                    while chunk:=response.read1(65536):
                        if stream:
                            stream.feed(chunk)
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    if stream and stream.buffer:
                        stream.feed(b'\n')
                    if stream and stream.finished and not stream.done:
                        self.wfile.write(b'\n\ndata: [DONE]\n\n')
                        self.wfile.flush()
            except urllib.error.HTTPError as error:
                # Provider error bodies can contain request metadata. Return only bounded status.
                self.json_response(error.code,{'error':{'message':'MiniMax Chat API returned HTTP '+str(error.code),'type':'provider_error'}})
            except (ValueError,TypeError):
                self.json_response(400,{'error':'Invalid Chat request'})
            except (BrokenPipeError,ConnectionResetError):
                pass
            except Exception:
                self.json_response(502,{'error':{'message':'MiniMax Chat connection failed','type':'provider_error'}})
    return Handler


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--port',type=int,default=11436)
    args=parser.parse_args()
    config=json.loads(pathlib.Path(args.config).read_text())
    if config['baseUrl'] not in ('https://api.minimax.cn/v1','https://api.minimax.io/v1'):
        raise ValueError('Use an official MiniMax endpoint')
    http.server.ThreadingHTTPServer(('127.0.0.1',args.port),handler(config)).serve_forever()
