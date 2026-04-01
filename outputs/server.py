#!/usr/bin/env python3
"""마크다운 검색 앱 로컬 서버"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError
import os
import sys
import socket
import json

LLM_BACKEND = 'http://localhost:1234/v1'

class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/search_in_md' or self.path == '/search_in_md/':
            self.path = '/markdown-search-app.html'
        elif self.path.startswith('/api/llm/'):
            return self._proxy_llm('GET')
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/llm/'):
            return self._proxy_llm('POST')
        self.send_error(405)

    def _proxy_llm(self, method):
        """LM Studio로의 요청을 프록시 (CORS 우회)"""
        target = LLM_BACKEND + self.path[len('/api/llm'):]
        try:
            body = None
            if method == 'POST':
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length) if length else None
            req = Request(target, data=body, method=method)
            req.add_header('Content-Type', 'application/json')
            with urlopen(req, timeout=180) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', len(data))
                self.end_headers()
                self.wfile.write(data)
        except URLError as e:
            err = json.dumps({'error': {'message': str(e.reason)}}).encode()
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(err))
            self.end_headers()
            self.wfile.write(err)
        except Exception as e:
            err = json.dumps({'error': {'message': str(e)}}).encode()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(err))
            self.end_headers()
            self.wfile.write(err)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")

def find_available_port(start_port=8080, max_attempts=10):
    """사용 가능한 포트 찾기"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # 명령줄에서 포트 지정 가능
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = find_available_port(3008)

    if port is None:
        print('❌ 사용 가능한 포트를 찾을 수 없습니다.')
        print('   기존 프로세스를 종료하세요: lsof -ti:8080 | xargs kill -9')
        sys.exit(1)

    try:
        server = HTTPServer(('localhost', port), CustomHandler)
        print(f'🚀 서버 시작: http://localhost:{port}/search_in_md')
        print('종료하려면 Ctrl+C를 누르세요')
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n서버 종료')
    except OSError as e:
        print(f'❌ 서버 시작 실패: {e}')
        print('   기존 프로세스를 종료하세요: lsof -ti:8080 | xargs kill -9')
