"""Entry point provisorio da serie 0.0.x — prova de pipeline, nao produto.

Este modulo existe para que `uvx overpower` responda algo *verificavel* nos dois
caminhos de instalacao do mapa: PyPI publico e indice Artifactory corporativo.
Ele reporta quatro coisas que so a execucao real responde:

- a **versao** que chegou, lida do metadado instalado e nao de uma constante,
  o que prova que o `dist-info` atravessou intacto;
- o **interpretador** que o `uvx` escolheu, com o caminho — num ambiente
  corporativo o caminho denuncia se o uv teve que *baixar* um Python, que vem
  do GitHub e nao do Artifactory, e e um modo de falha que a pesquisa de
  empacotamento nao cobriu;
- a **plataforma**, porque a maquina corporativa e Windows;
- o **payload**, se presente: tamanho e digest, que e a prova de que conteudo
  pesado atravessou o proxy sem truncar.

A superficie de comandos de verdade esta decidida em
https://github.com/panlabs-tech/overpower/issues/8 e nasce na v0.1.0. Aqui nao
ha parsing de argumento de proposito: qualquer invocacao imprime o mesmo
relatorio e sai 0, para que `overpower`, `overpower --version` e
`uvx overpower@latest` sejam todos utilizaveis como smoke test.
"""

from __future__ import annotations

import hashlib
import platform
import sys
from importlib import metadata, resources

_PAYLOAD = ("_payload", "probe.bin")


def _version() -> str:
    try:
        return metadata.version("overpower")
    except metadata.PackageNotFoundError:
        return "desinstalado (rodando do fonte)"


def _payload() -> str:
    # `importlib.resources`, nunca caminho de arquivo: e o unico acesso que
    # funciona igual instalado em disco solto e dentro de um zip.
    node = resources.files("overpower")
    for part in _PAYLOAD:
        node = node / part
    if not node.is_file():
        return "ausente (build sem probe)"
    data = node.read_bytes()
    return f"{len(data)} bytes · sha256 {hashlib.sha256(data).hexdigest()[:16]}"


def main() -> int:
    print(f"overpower {_version()}")
    print(f"python    {platform.python_implementation()} {platform.python_version()} · {sys.platform}")
    print(f"exe       {sys.executable}")
    print(f"payload   {_payload()}")
    return 0
