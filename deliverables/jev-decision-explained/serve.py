"""Local read-only preview of this deck and explicitly public evidence."""
import pathlib,http.server,urllib.parse,argparse
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PUBLIC=[ROOT/'research/decision-skills-l40-20261018',HERE,ROOT/'skills',ROOT/'research/jev-report-qa-20261018',ROOT/'research/jev-qwen35-9b-20261016',ROOT/'research/kv-concurrency-20261016',ROOT/'research/pplx-timeshare-20261012']
FILES=[ROOT/'docs'/n for n in ['Jev实验主线与9B分类收益解读_20261018.md','Jev决策模型报告答疑与通俗解读_20261018.md','首诊断弱标签RCU子串误判审计_20261018.md','决策模型开发与微调复现指南_20261018.md']]
class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self,path):
        raw=urllib.parse.unquote(urllib.parse.urlsplit(path).path);s=raw.lstrip('/')
        if raw in ['/','/deck.html']:p=HERE/'deck.html'
        elif raw.startswith('/media/') or raw.startswith('/rendered/') or '/' not in s:p=HERE/s
        else:p=ROOT/s
        p=p.resolve()
        return str(p if p in FILES or any(p.is_relative_to(d) for d in PUBLIC) else HERE/'__not_public__')
    def list_directory(self,path):self.send_error(403,'Directory listing disabled');return None
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8795);a=p.parse_args()
    http.server.ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
