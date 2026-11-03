"""Servidor local do jogo (o Pyodide precisa de http://, nao abre direto por file://).

    python3 tools/serve.py [porta]

Imprime o endereco da rede local, pra abrir no celular. Sem cache: o celular
pega a versao nova a cada refresh.
"""

import socket
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PORTA = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript", ".py": "text/plain"}

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"  {self.address_string()} {fmt % args}\n")


def ip_local() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> None:
    servidor = ThreadingHTTPServer(("0.0.0.0", PORTA), partial(Handler, directory=str(RAIZ)))
    servidor.daemon_threads = True
    print("Da Lona à Toga")
    print(f"  neste computador: http://localhost:{PORTA}")
    print(f"  no celular:       http://{ip_local()}:{PORTA}")
    print("  (ctrl+c para parar)\n")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nparado.")


if __name__ == "__main__":
    main()
