"""Loopback preview limited to public slide and concurrency-study directories."""
import pathlib,argparse,urllib.parse,http.server
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PUBLIC=[HERE,ROOT/'research/kv-concurrency-20261015',ROOT/'research/kv-concurrency-20261016']
class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self,path):
        raw=urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        relative=raw.lstrip('/')
        if raw in ['/','/deck.html']:candidate=HERE/'deck.html'
        elif raw.startswith('/media/'):candidate=HERE/relative
        elif '/' not in relative:candidate=HERE/relative
        else:candidate=ROOT/relative
        candidate=candidate.resolve()
        if any(candidate.is_relative_to(p) for p in PUBLIC):return str(candidate)
        return str(HERE/'__not_public__')
    def list_directory(self,path):self.send_error(403,'Directory listing disabled');return None
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8793);a=p.parse_args()
    print(f'Preview http://127.0.0.1:{a.port}/deliverables/kernel-insight-system/deck.html#49',flush=True)
    http.server.ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
