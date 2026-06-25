import os
import json
import http.server
import socketserver
import threading
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
                "<!DOCTYPE html><html><head><title>Projects</title>",
                "<style>",
                "body { font-family: sans-serif; background: #e9e1cf; padding: 20px; color: #333; }",
                ".card { background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: transform 0.2s; display: block; }",
                ".card:hover { transform: translateY(-2px); }",
                "a { text-decoration: none; color: inherit; }",
                "h2 { margin-top: 0; color: #2c3e50; }",
                "</style></head><body><h1>Projects</h1>"
            ]
            for p in projects:
                html.append(f"<a href='/{p['id']}/'><div class='card'><h2>{p.get('name', p['id'])}</h2><p>{p.get('description', '')}</p></div></a>")
            if not projects:
                html.append("<p>No projects found.</p>")
            html.append("</body></html>")
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
            elif first in ['cad', 'library', 'drawings', 'evidence']:
                file_path = ROOT / path.lstrip('/')
                self._serve_file(file_path)
                return
            else:
                project_id = first
                # GET /<project>/ -> viewer/index.html injected with project context
                if len(parts) == 1 and path.endswith('/'):
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
