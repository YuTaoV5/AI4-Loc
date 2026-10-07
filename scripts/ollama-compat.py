"""Loopback-only dsh/OpenAI compatibility adapter; no credentials or logs persisted."""
import http.server,json,urllib.request,urllib.error
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):self.forward()
    def do_POST(self):self.forward()
    def forward(self):
        if self.path not in ['/v1/models','/v1/chat/completions']:return self.send_error(404)
        size=int(self.headers.get('Content-Length','0'))
        if size>2*1024*1024:return self.send_error(413)
        body=None
        if self.command=='POST':
            payload=json.loads(self.rfile.read(size))
            if not str(payload.get('model','')).startswith('qwen3.8:27b-kernel-'):return self.send_error(400)
            # Ollama maps OpenAI reasoning_effort=none to think=false on boolean thinking models.
            payload['reasoning_effort']='none'
            body=json.dumps(payload).encode()
        request=urllib.request.Request('http://127.0.0.1:11434'+self.path,data=body,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=180) as response:
                self.send_response(response.status);self.send_header('Content-Type',response.headers.get('Content-Type','application/json'));self.send_header('Connection','close');self.end_headers()
                while chunk:=response.read1(65536):self.wfile.write(chunk);self.wfile.flush()
        except (BrokenPipeError,ConnectionResetError):pass
        except urllib.error.HTTPError as error:self.send_error(error.code)
        except Exception:self.send_error(502)
        self.close_connection=True
if __name__=='__main__':http.server.ThreadingHTTPServer(('127.0.0.1',11435),Handler).serve_forever()
