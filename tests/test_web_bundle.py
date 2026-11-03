"""MODULOS em pyodide-bridge.js tem que listar todo .py do pacote.

Sem isso o navegador da 404 em tempo de execucao, e so na primeira vez que
alguem abre a pagina. Tambem confere que o HTML carrega o que existe.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PACOTE = RAIZ / "py" / "lonatoga"


def test_modulos_lista_exatamente_os_arquivos_do_pacote():
    js = (RAIZ / "pyodide-bridge.js").read_text(encoding="utf-8")
    bloco = re.search(r"export const MODULOS = \[(.*?)\];", js, re.S).group(1)
    listados = set(re.findall(r'"([^"]+\.py)"', bloco))
    em_disco = {str(p.relative_to(PACOTE)) for p in PACOTE.rglob("*.py")}
    assert listados == em_disco, (sorted(listados ^ em_disco))


def test_diretorios_do_fs_virtual_cobrem_os_modulos():
    js = (RAIZ / "pyodide-bridge.js").read_text(encoding="utf-8")
    dirs = set(re.findall(r'"(/jogo[^"]*)"', js))
    for p in PACOTE.rglob("*.py"):
        pai = f"/jogo/lonatoga/{p.parent.relative_to(PACOTE)}".rstrip("/.")
        assert pai in dirs or pai == "/jogo/lonatoga", pai


def test_html_aponta_para_arquivos_que_existem():
    html = (RAIZ / "index.html").read_text(encoding="utf-8")
    for ref in re.findall(r'(?:src|href)="\./([^"]+)"', html):
        assert (RAIZ / ref).exists(), ref


def test_todo_import_do_app_existe():
    js = (RAIZ / "app.js").read_text(encoding="utf-8")
    for ref in re.findall(r'from "\./([^"]+)"', js):
        assert (RAIZ / ref).exists(), ref
