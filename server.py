import os
import json
import http.server
import socketserver
import threading
from html import escape
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent

class ProjectHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = unquote(self.path.split('?', 1)[0])

        if path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            projects = []
            projects_dir = ROOT / "projects"
            if projects_dir.exists():
                for pdir in projects_dir.iterdir():
                    if pdir.is_dir():
                        pjson = pdir / "project.json"
                        if pjson.exists():
                            try:
                                with open(pjson, 'r') as f:
                                    data = json.load(f)
                                    data['id'] = pdir.name
                                    projects.append(data)
                            except Exception:
                                pass
            
            html = [
                "<!DOCTYPE html><html><head><title>AssemblyBot Index</title>",
                "<meta name='viewport' content='width=device-width, initial-scale=1'>",
                "<style>",
                ":root{--paper:#e9e1cf;--ink:#25231f;--muted:#696356;--rule:rgba(37,35,31,.46);--soft:rgba(255,255,255,.32);--red:#9b2f2f;--green:#365f45;}",
                "*{box-sizing:border-box}",
                "html,body{margin:0;min-height:100%;}",
                "body{font-family:'Consolas','SFMono-Regular','Liberation Mono',monospace;color:var(--ink);background-color:var(--paper);",
                "background-image:linear-gradient(rgba(37,35,31,.075) 1px,transparent 1px),linear-gradient(90deg,rgba(37,35,31,.075) 1px,transparent 1px),linear-gradient(rgba(37,35,31,.16) 1px,transparent 1px),linear-gradient(90deg,rgba(37,35,31,.16) 1px,transparent 1px);",
                "background-size:10px 10px,10px 10px,50px 50px,50px 50px;padding:22px;}",
                ".sheet{max-width:1180px;min-height:calc(100vh - 44px);margin:0 auto;border:2px solid var(--ink);background:rgba(233,225,207,.58);box-shadow:0 0 0 6px rgba(233,225,207,.9),0 0 0 7px var(--rule);position:relative;}",
                ".sheet:before,.sheet:after{content:'';position:absolute;width:54px;height:54px;border-color:var(--ink);border-style:solid;pointer-events:none}.sheet:before{left:14px;top:14px;border-width:2px 0 0 2px}.sheet:after{right:14px;bottom:14px;border-width:0 2px 2px 0}",
                "header{display:grid;grid-template-columns:1fr 360px;border-bottom:2px solid var(--ink);min-height:126px;}",
                ".title{padding:22px 26px 18px;display:grid;align-content:end;}",
                ".eyebrow{font-size:11px;color:var(--red);text-transform:uppercase;letter-spacing:.08em;margin-bottom:9px}",
                "h1{margin:0 0 10px;font-size:34px;line-height:1;letter-spacing:0;font-weight:700;text-transform:uppercase;}",
                ".sub{font-size:12px;color:var(--muted);line-height:1.45;max-width:760px;text-transform:uppercase;}",
                ".stamp{border-left:2px solid var(--ink);min-width:260px;display:grid;grid-template-columns:112px 1fr;font-size:11px;text-transform:uppercase;background:rgba(255,255,255,.10);}",
                ".stamp div{padding:8px 10px;border-bottom:1px solid var(--rule);}",
                ".stamp div:nth-last-child(-n+2){border-bottom:0}",
                ".stamp .k{color:var(--muted);background:rgba(255,255,255,.18);}",
                ".toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:10px 26px;border-bottom:1px solid var(--rule);font-size:12px;color:var(--muted);}",
                ".legend{display:flex;gap:18px;flex-wrap:wrap}.legend span:before{content:'';display:inline-block;width:18px;height:1px;background:var(--ink);vertical-align:middle;margin-right:7px}",
                ".bom-title{display:grid;grid-template-columns:44px 1fr 155px 155px;border-bottom:2px solid var(--ink);background:rgba(255,255,255,.18);}",
                ".bom-title div{padding:9px 12px;border-right:1px solid var(--rule);font-size:11px;text-transform:uppercase;color:var(--muted)}.bom-title div:last-child{border-right:0}",
                ".table{display:grid;grid-template-columns:44px minmax(190px,1.25fr) minmax(220px,2fr) minmax(190px,1fr);}",
                ".cell{min-height:52px;padding:12px 12px;border-bottom:1px solid rgba(37,35,31,.28);border-right:1px solid rgba(37,35,31,.28);font-size:12px;line-height:1.35;background:rgba(233,225,207,.38);}",
                ".cell:nth-child(4n){border-right:0}",
                ".head{min-height:32px;padding-top:8px;color:var(--muted);font-size:11px;text-transform:uppercase;background:rgba(255,255,255,.24);}",
                ".idx{color:var(--muted);text-align:right;padding-right:14px}",
                "a.project{display:contents;color:inherit;text-decoration:none}",
                "a.project .cell{transition:background .12s ease,color .12s ease}",
                "a.project:hover .cell{background:rgba(255,255,255,.44);color:#111}",
                ".name{font-weight:700;text-transform:uppercase}.desc{color:#3e3b35}.path{color:var(--muted);word-break:break-all}",
                ".status{color:var(--green);font-weight:700}",
                ".empty{padding:26px 20px;font-size:13px;color:var(--muted)}",
                "@media(max-width:760px){body{padding:12px}.sheet{max-width:none;min-height:calc(100vh - 24px)}header{grid-template-columns:1fr}.stamp{border-left:0;border-top:2px solid var(--ink);min-width:0}.toolbar{align-items:flex-start;flex-direction:column}.bom-title{grid-template-columns:36px 1fr}.bom-title div:nth-child(n+3){display:none}.table{grid-template-columns:36px 1fr}.cell{border-right:0}.head:nth-child(n+3),a.project .cell:nth-child(4n),a.project .cell:nth-child(4n-1){display:none}.desc,.path{display:none}h1{font-size:25px}}",
                "</style></head><body><main class='sheet'><header><section class='title'><div class='eyebrow'>Controlled Assembly Records</div><h1>Project Index</h1>",
                "<div class='sub'>Canonical assemblies, inspection views, and verification artifacts laid out as a shop drawing bill of materials.</div></section>",
                "<section class='stamp'><div class='k'>Drawing</div><div>AB-INDEX</div><div class='k'>Sheet</div><div>01 / 01</div><div class='k'>Origin</div><div>127.0.0.1</div><div class='k'>Scale</div><div>Viewer Native</div><div class='k'>Status</div><div class='status'>Live</div></section></header>",
                "<div class='toolbar'><div class='legend'><span>Open assembly viewer</span><span>Canonical project folder</span></div>",
                f"<div>{len(projects)} project{'s' if len(projects) != 1 else ''}</div></div>"
            ]
            if projects:
                html.append("<section class='bom-title'><div>Item</div><div>Assembly Record</div><div>Gate</div><div>Action</div></section>")
                html.append("<section class='table' aria-label='Project list'>")
                html.append("<div class='cell head idx'>No.</div><div class='cell head'>Assembly</div><div class='cell head'>Description</div><div class='cell head'>Canonical</div>")
            for n, p in enumerate(projects, 1):
                pid = escape(p['id'])
                name = escape(p.get('name', p['id']))
                desc = escape(p.get('description', ''))
                canonical = escape(p.get('canonical_assembly', 'project.json'))
                html.append(f"<a class='project' href='/{pid}/'><div class='cell idx'>{n:02d}</div><div class='cell name'>{name}</div><div class='cell desc'>{desc}</div><div class='cell path'>{pid}/{canonical}</div></a>")
            if projects:
                html.append("</section>")
            else:
                html.append("<div class='empty'>No project.json files found under /projects.</div>")
            html.append("</main></body></html>")
            self.wfile.write("".join(html).encode("utf-8"))
            return

        parts = [p for p in path.split('/') if p]
        
        if len(parts) >= 1:
            first = parts[0]
            if first == '_app':
                rel_path = "/".join(parts[1:])
                file_path = ROOT / "viewer" / rel_path
                self._serve_file(file_path)
                return
            elif first in ['cad', 'library', 'drawings', 'evidence', 'out']:
                file_path = ROOT / path.lstrip('/')
                self._serve_file(file_path)
                return
            else:
                project_id = first
                # GET /<project>/ -> viewer/index.html injected with project context
                if len(parts) == 1:
                    if not path.endswith('/'):
                        self.send_response(301)
                        self.send_header("Location", path + "/")
                        self.end_headers()
                        return
                    viewer_html = ROOT / "viewer" / "index.html"
                    if not viewer_html.exists():
                        self.send_error(404, "viewer/index.html not found")
                        return
                    with open(viewer_html, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    injection = f"<script>window.PROJECT_ID = '{project_id}';</script>"
                    if "<head>" in content:
                        content = content.replace("<head>", f"<head>\n  {injection}")
                    else:
                        content = injection + content
                    
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(content.encode("utf-8"))
                    return
                elif len(parts) > 1:
                    rel_path = "/".join(parts[1:])
                    file_path = ROOT / "projects" / project_id / rel_path
                    self._serve_file(file_path)
                    return

        self.send_error(404, "Not Found")

    def _serve_file(self, file_path):
        if not file_path.exists():
            self.send_error(404, "File not found")
            return
        if file_path.is_dir():
            self.send_error(403, "Directory listing denied")
            return
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            ext = file_path.suffix.lower()
            if ext == '.html':
                ctype = 'text/html'
            elif ext == '.js':
                ctype = 'application/javascript'
            elif ext == '.css':
                ctype = 'text/css'
            elif ext == '.json':
                ctype = 'application/json'
            elif ext == '.png':
                ctype = 'image/png'
            elif ext == '.glb':
                ctype = 'model/gltf-binary'
            elif ext == '.gltf':
                ctype = 'model/gltf+json'
            elif ext in ['.step', '.stp']:
                ctype = 'application/octet-stream'
            else:
                ctype = 'application/octet-stream'
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))

def serve(port=8000, block=False):
    socketserver.TCPServer.allow_reuse_address = True
    try:
        httpd = socketserver.TCPServer(("127.0.0.1", port), ProjectHandler)
    except OSError as e:
        if e.errno in (98, 10048): # Address already in use
            print(f"Port {port} already in use, assuming server is running...")
            return None
        raise

    if block:
        print(f"Serving on http://127.0.0.1:{port}/")
        httpd.serve_forever()
    else:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        return httpd

if __name__ == "__main__":
    serve(block=True)
