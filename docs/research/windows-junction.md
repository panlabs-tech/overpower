# Criação de junction no Windows: API privada, subprocesso ou ctypes

Pesquisa que resolve o ticket [Criação de junction no Windows: API privada ou subprocesso](https://github.com/panlabs-tech/overpower/issues/19), deixado em aberto por [Aterrissagem projeto × global](https://github.com/panlabs-tech/overpower/issues/5) §5.4.

Data: 2026-08-01. Tudo abaixo é fonte primária (código do CPython nas tags oficiais, doc do CPython, doc da Microsoft, código do `actions/runner-images`) **ou medido** numa máquina Windows 11 real, alcançada por interop do WSL2. Cada afirmação medida traz o comando e o resultado.

---

## Resumo executivo

**Recomendação: `_winapi.CreateJunction`.** A pergunta acaba aqui — como o próprio ticket previa, se ela for viável, não há decisão de axioma a tomar.

As duas premissas que davam peso à alternativa **estão erradas**:

1. **"Sem doc pública"** — é falso. `_winapi.CreateJunction` **está documentado** no manual oficial do CPython, na tabela de *audit events*, com a assinatura exata `src_path, dst_path`. O nome e a aridade fazem parte de uma superfície versionada e publicada.
2. **"Não há garantia de que exista em toda build de CPython para Windows"** — é falso na prática. `_winapi` é módulo **builtin**, listado incondicionalmente na tabela `_PyImport_Inittab` de `PC/config.c`. Não é um `.pyd` que um instalador enxuto possa deixar de fora: ou a build é CPython para Windows, ou não é.

E há um terceiro fato que fecha a questão: **`CreateJunction` existe desde o CPython 3.5.0** (2015) e **cinco arquivos de teste da própria stdlib dependem dele** hoje — `test_os`, `test_ntpath`, `test_shutil`, `test_pathlib`, `test_os/test_windows`. Removê-la quebraria a suíte do CPython.

O `mklink /J` não perde só no axioma. Perde em **correção**, medido: com um `src` inexistente ele sai **`rc=0` e cria uma junction pendurada**, enquanto `_winapi.CreateJunction` levanta `FileNotFoundError`. Um instalador que cria equipamento quebrado e reporta sucesso é pior que um que falha.

**A pesquisa também derruba a pergunta que estava por trás do ticket.** A escada de §5.4 supunha um probe antes de escolher o degrau. No Windows **não há degrau a escolher**: a junction funciona **com ou sem privilégio** — medido nas duas condições. O probe de symlink de §5.2 não deve rodar no Windows.

E encontrou **três armadilhas de remoção** que valem mais que a decisão de API — a mesma classe de armadilha que [Semântica de escrita](https://github.com/panlabs-tech/overpower/issues/9) catalogou para symlink em POSIX, replicada em junction no Windows, com um agravante: `os.path.islink()` devolve **`False`** para uma junction, e `shutil.rmtree()` **mesmo assim a recusa** (§7).

---

## 1. O ambiente de medição

O que dá peso aos números abaixo é a configuração da máquina: ela é **exatamente** o caso corporativo que a junction existe para resolver.

```
user                              : ALIENWARE-X14\panin
isAdmin (token elevado)           : False
BUILTIN\Administrators            : "Group used for deny only"
Mandatory Label                   : Medium Mandatory Level
SeCreateSymbolicLinkPrivilege     : ausente do token (whoami /priv)
AllowDevelopmentWithoutDevLicense : não definida  → Developer Mode DESLIGADO
Windows                           : 11, build 10.0.26200
```

Prova de que o privilégio realmente falta — não é suposição:

```python
>>> os.symlink(src, dst, target_is_directory=True)
OSError: [WinError 1314] A required privilege is not held by the client
```

`WinError 1314` é `ERROR_PRIVILEGE_NOT_HELD`, o mesmo código que §5.3 mapeia para `windows-privilege-not-held`. **Esta máquina é o cenário de falha.**

Interpretadores medidos, todos alcançados de dentro do WSL2 por interop:

| Interpretador | Origem | `_winapi.CreateJunction` |
| :--- | :--- | :--- |
| CPython 3.10.9 | python.org | presente |
| CPython 3.12.10 | python.org | presente |
| CPython 3.14.3 | PyManager | presente |

Em todos, `_winapi.__file__` é `<builtin>` — compilado no interpretador, não carregado de um `.pyd`.

---

## 2. `_winapi.CreateJunction` — o que é fato

### 2.1 Existe desde o CPython 3.5.0

Contagem de ocorrências de `CreateJunction` em `Modules/_winapi.c`, lida direto das tags oficiais:

| Tag | Ocorrências |
| :--- | :--- |
| `v3.2.6` | 0 |
| `v3.3.7` | 0 |
| `v3.4.10` | 0 |
| `v3.5.0` | 2 |
| `v3.5.10` | 2 |
| `v3.7.0` | 2 |
| `v3.8.0` | 3 |
| `v3.12.0` | 3 |
| `v3.14.0` | 3 |

A função nasce na **3.5.0**. A contagem sobe para 3 na 3.8 porque o Argument Clinic passou a gerar um bloco a mais, não porque a API mudou. **Onze anos de presença contínua**, atravessando dez ciclos de release.

O piso do projeto é `requires-python = ">=3.12"` ([#2](https://github.com/panlabs-tech/overpower/issues/2)). A margem é de sete versões menores.

### 2.2 É builtin — não há build de Windows sem ele

`PC/config.c` na `v3.14.0`:

```c
extern PyObject* PyInit__winapi(void);
...
    /* XXX Should _winapi go in a WIN32 block?  not WIN64? */
    {"_winapi", PyInit__winapi},
```

A entrada é **incondicional** na tabela de módulos builtin. Não há `#ifdef` de recorte, não há alvo de build que o torne opcional. Isso bate com o medido: `_winapi.__file__ == '<builtin>'` nos três interpretadores.

A consequência prática é a que interessa: **`try: import _winapi` não é a checagem certa**, porque o import nunca falha num CPython para Windows. A checagem defensiva útil, se houver, é `hasattr(_winapi, "CreateJunction")`.

### 2.3 Está documentado — na tabela de audit events

O código emite um evento de auditoria (`Modules/_winapi.c`, `v3.14.0`):

```c
if (PySys_Audit("_winapi.CreateJunction", "uu", src_path, dst_path) < 0) {
    return NULL;
}
```

E esse evento **consta do manual oficial**, em `Doc/library/audit_events.rst`, publicado em <https://docs.python.org/3/library/audit_events.html>:

> `_winapi.CreateJunction` | `src_path`, `dst_path`

Sejamos precisos sobre o que isso compra e o que não compra. A doc documenta o **evento**, não a função como API pública — não há entrada dela em `Doc/library/`, e o Argument Clinic não define docstring (medido: `CreateJunction.__doc__ is None`). Mas o nome, a aridade e a ordem dos argumentos estão **publicados e versionados**. A premissa do ticket — *"sem doc pública"* — não sobrevive: mudar essa assinatura seria mudar documentação publicada.

Colateral que o overpower deve conhecer: como há evento de auditoria, um hook instalado por `sys.addaudithook` pode **bloquear** a chamada. Num ambiente corporativo com hardening de Python isso é um modo de falha real, e ele se apresenta como uma exceção vinda do hook — motivo a mais para o `except` do overpower ser largo e cair para cópia, não para `except OSError` estreito.

### 2.4 A stdlib depende dela

Busca de código em `python/cpython` por `CreateJunction` — 8 arquivos, dos quais **cinco são testes**:

```
Modules/_winapi.c
Modules/clinic/_winapi.c.h
Doc/library/audit_events.rst
Lib/test/test_shutil.py
Lib/test/test_ntpath.py
Lib/test/test_os/test_windows.py
Lib/test/test_os/test_os.py
Lib/test/test_pathlib/test_pathlib.py
```

Este é o argumento de estabilidade mais forte disponível, e é melhor que qualquer promessa: **a suíte de testes do CPython quebra se a função sumir.** Uma API privada da qual o próprio projeto depende em cinco módulos de teste não é candidata a remoção silenciosa.

### 2.5 O que ela faz por dentro

Leitura de `_winapi_CreateJunction_impl` na `v3.14.0`, resumida no que muda decisão:

1. Rejeita `src_path` já prefixado com `\??\` (`ERROR_INVALID_PARAMETER`).
2. Emite o audit event.
3. Habilita **temporariamente** `SE_RESTORE_NAME` no token do processo.
4. **Valida que `src_path` existe** — `GetFileAttributesW(src_path) == INVALID_FILE_ATTRIBUTES` aborta. *É daqui que vem o `FileNotFoundError` que o `mklink` não dá.*
5. Resolve `src_path` para absoluto com `GetFullPathNameW` — por isso caminho relativo funciona e é gravado absoluto.
6. Monta o `REPARSE_DATA_BUFFER` com tag `IO_REPARSE_TAG_MOUNT_POINT`, com *substitute name* prefixado de `\??\` e *print name* sem prefixo.
7. `CreateDirectoryW` no destino, depois `DeviceIoControl` com `FSCTL_SET_REPARSE_POINT`.

Sobre o passo 3: o comentário do próprio CPython no passo 6 é revelador —

> *"REPARSE_DATA_BUFFER usage is heavily under-documented, especially for junction points. Here's what I've learned along the way…"*

Guardem esta frase; ela é o argumento central contra reimplementar isso à mão (§4).

**Uma nota de versão.** O commit [`de4ced54e`](https://github.com/python/cpython/commit/de4ced54e) (*gh-114096: Restore privileges in `_winapi.CreateJunction` after creating the junction*, 2024-01-16) corrigiu o fato de a função **deixar `SE_RESTORE_NAME` habilitado** no token depois de retornar — *"This avoids impact on later parts of the application which may be able to do things they otherwise shouldn't."* Backports mergeados no mesmo dia para 3.12 (PR 114134) e 3.11 (PR 114135). Logo **3.12.0 e 3.12.1 não têm o fix**; 3.12.2 (fev/2024) em diante têm. O impacto é limitado a processos que **de fato detêm** `SE_RESTORE_NAME` — num token de usuário comum o `AdjustTokenPrivileges` é inócuo. Não muda a recomendação; entra como nota, e como argumento marginal a favor de `requires-python = ">=3.12"` com aviso, ou de um piso em `3.12.2` se algum dia isso importar.

### 2.6 Assinatura e tipos aceitos — medido

```
__text_signature__ : ($module, src_path, dst_path, /)
__doc__            : None
```

Posicionais apenas. `src_path` é o **alvo**; `dst_path` é a **junction criada**. Confirmado lendo através dela.

| Entrada | Resultado |
| :--- | :--- |
| `str` absoluto | ok |
| `str` relativo | ok — gravado absoluto (`GetFullPathNameW`) |
| `pathlib.Path` | **`TypeError: CreateJunction() argument 1 must be str, not WindowsPath`** |
| `bytes` | **`TypeError: ... must be str, not bytes`** |

O clinic declara `LPCWSTR`, que não aceita o protocolo `os.PathLike`. **O `os.fspath()`/`str()` é responsabilidade de quem chama** — e num código que trafega `pathlib.Path` em todo lugar, como o overpower vai trafegar, essa é a fronteira exata onde o `pyright` strict de [#2](https://github.com/panlabs-tech/overpower/issues/2) ganha o seu sustento.

Erros, medidos, todos como exceção Python idiomática:

| Caso | Exceção |
| :--- | :--- |
| `dst` já existe | `FileExistsError` — `[WinError 183]` |
| `src` não existe | `FileNotFoundError` — `[WinError 2]`, e **nada é criado** |
| `src` é um **arquivo** | **nenhuma** — cria junction quebrada (§7.4) |

### 2.7 Onde ela não existe: PyPy

Busca de código em `pypy/pypy` por `CreateJunction`: **0 resultados**. O PyPy implementa `_winapi` para o `subprocess`, mas não expõe `CreateJunction`.

Peso disso para o overpower: **baixo, e coberto**. O `uv`/`uvx` instala CPython por padrão, e o caminho de instalação recomendado do produto é `uvx overpower@latest`. Um usuário de PyPy no Windows cai no `hasattr` e degrada para cópia — que é o comportamento correto, não uma falha. Também não existe em Python de Cygwin, mas ali `sys.platform == 'cygwin'`, não `'win32'`, e o ramo nem é alcançado.

---

## 3. `mklink /J` — medido, e pior em três pontos

### 3.1 `mklink` não é um executável

```python
subprocess.run(["mklink", "/J", dst, src])
→ FileNotFoundError: [WinError 2] The system cannot find the file specified
```

`mklink` é **builtin do `cmd.exe`**. Não há binário. O uso obrigatório é `["cmd", "/c", "mklink", "/J", dst, src]`, o que torna a dependência **do interpretador de comandos**, não de um utilitário do SO — distinção que importa para a leitura do axioma 1, e que o enunciado do ticket ainda não tinha.

### 3.2 Sai `rc=0` criando junction pendurada

Este é o achado que decide, e não é sobre axioma:

```
-- src inexistente --
   rc: 0
   out: 'Junction created for ...\jD <<===>> ...\nada'
   criou dangling: True
```

O `mklink /J` **reporta sucesso** e deixa uma junction apontando para o vazio. A `_winapi.CreateJunction`, no mesmo caso, levanta `FileNotFoundError` e não cria nada.

Para o overpower isso é diferença de correção direta: uma junction pendurada em `~/.claude/skills/<nome>` é equipamento que o Claude Code lista e não consegue ler, num diretório que o axioma 2 diz não ter manifesto. O erro só aparece no uso, longe da instalação.

### 3.3 A saída é localizada; só o `rc` presta

```
out: 'Junction created for C:\...\jB <<===>> C:\...\canon'
```

Texto em inglês nesta máquina porque o Windows está em inglês. Num Windows pt-BR — que é o caso do público-alvo corporativo — a string muda. **Qualquer parsing de `stdout` é dependente de locale.** O `rc` funciona (`0` sucesso, `1` para `dst` já existente), mas note em §3.2 que o `rc` **não** distingue sucesso de junction pendurada.

Medido também: erro vai para `stderr` (`Cannot create a file when that file already exists.`) e, quando o `cwd` é UNC, o `cmd.exe` **polui o `stderr`** com três linhas de aviso (`UNC paths are not supported. Defaulting to Windows directory.`) antes de qualquer coisa. Parsing de `stderr` é ainda pior que o de `stdout`.

Pontos em que `mklink` **não** falhou: caminhos com espaço e com `&` passam corretamente quando os argumentos vão como lista (sem `shell=True`), e `CREATE_NO_WINDOW` está disponível para evitar flash de console.

### 3.4 O axioma 1

Não precisa ser lido. O ticket enunciou a condição — *"Ele é o caminho que não fere axioma nenhum — se for viável, a pergunta acaba aqui"* — e `_winapi.CreateJunction` é viável. Além disso, `mklink` já está **dominado**: perde em correção (§3.2) e em robustez (§3.3) contra as duas alternativas, então não é escolhido nem numa leitura permissiva do axioma. **A decisão de leitura do axioma 1 fica sem custo, e não precisa ser tomada neste ticket.**

---

## 4. A terceira saída que o ticket não listou: `ctypes`

Uma junction é apenas um diretório com um reparse point. Dá para escrevê-la com `ctypes` sobre Win32 **documentado** — `CreateFileW` + `DeviceIoControl(FSCTL_SET_REPARSE_POINT)` — sem stdlib privada e sem subprocesso. Isto satisfaz o axioma 1 na leitura mais estrita possível.

**Implementado e medido nesta máquina** (3.12.10, sem privilégio). Funciona, e o resultado é indistinguível:

```
criou: True
listdir: ['SKILL.md']
read-through: canonical bytes
reparse_tag: 0xa0000003
isjunction: True
readlink: \\?\C:\...\canon
rmdir preservou alvo: True
```

**Custo medido: 38 linhas não vazias** — declarações de `argtypes`/`restype`, `struct.pack` manual do `REPARSE_DATA_BUFFER`, `use_last_error`, gestão de handle e limpeza do diretório em cada caminho de falha. Contra **uma linha**.

E o custo real não é o tamanho: é que essas 38 linhas **reimplementam exatamente o que o CPython já embarca**, incluindo o buffer que o comentário do próprio CPython chama de *"heavily under-documented"*. Um bug de empacotamento aqui não dá exceção — dá um reparse point malformado, que é corrupção silenciosa no `~/.claude/skills` do usuário.

Vale registrar como **saída de contingência documentada**: se algum dia `_winapi.CreateJunction` sumir, a substituição é conhecida, medida e cabe em 38 linhas. Não é o caminho da v0.1.0.

---

## 5. As três saídas, lado a lado

| | `_winapi.CreateJunction` | `ctypes` + `DeviceIoControl` | `cmd /c mklink /J` |
| :--- | :--- | :--- | :--- |
| Linhas de código | **1** | **38** | ~6 (+ parsing) |
| Funciona sem privilégio | **sim** (medido) | **sim** (medido) | sim |
| `src` inexistente | `FileNotFoundError` | `NotADirectoryError` (validação nossa) | **`rc=0`, junction pendurada** |
| `src` é arquivo | **cria lixo em silêncio** | `NotADirectoryError` (validação nossa) | cria lixo |
| Depende de `cmd.exe` | não | não | **sim** |
| Sensível a locale | não | não | **sim** (stdout/stderr) |
| Tensão com axioma 1 | nenhuma | nenhuma | **sim** |
| Estabilidade | 3.5.0+, 5 testes da stdlib, audit event documentado | Win32 documentado e estável | builtin do `cmd` |
| Ausente em | PyPy | — | — |
| Risco residual | API privada sem contrato formal | **corrupção silenciosa** por bug de packing | equipamento quebrado com sucesso reportado |

---

## 6. A escada, corrigida: no Windows não há degrau a escolher

§5.4 da pesquisa anterior desenhou assim:

```
Windows:  junction (absoluta)  →  cópia
          [symlink só se Developer Mode estiver ligado]
```

A medição corrige a **motivação**, não o desenho. A junction funcionou nesta máquina **sem** privilégio e funciona igualmente **com** — não há condição em que symlink sirva e junction não. Ou seja:

**O probe de symlink de §5.2 não deve rodar no Windows.** Ele mede uma capacidade que não muda decisão nenhuma, custa I/O e introduz um ramo que não pode ser exercitado (§8.3). No Windows: tenta junction, cai para cópia se ela falhar. É exatamente o que o `npx skills` faz (`src/installer.ts:255-257`) — e agora sabemos que a razão é mais forte do que "junction dispensa privilégio": é que **não há nada a decidir**.

Isso **não** elimina o fallback de cópia (a terceira saída do ticket, que permanece necessária). Junction não serve em três casos:

- **Sistema de arquivos sem reparse point** — FAT32, exFAT. Reparse points são NTFS/ReFS. Um `%USERPROFILE%` em pen drive ou partição exFAT cai em cópia.
- **Alvo em rede.** A Microsoft é explícita: uma junction liga *"directories located on different local volumes on the same computer"*. `$HOME` redirecionado para share SMB — comum em domínio corporativo — não é servido por junction.
- **PyPy** (§2.7).

Nesses casos vale a decisão 6 do [#9](https://github.com/panlabs-tech/overpower/issues/9): cópia real, e **reportar a degradação**. Reportar não fere o axioma 2 — gravar no alvo, sim.

Não foi possível medir volumes múltiplos: esta máquina só tem `C:`. Fica em aberto (§10).

---

## 7. Como o Python enxerga uma junction — as armadilhas medidas

Esta seção vale mais que a decisão de API. É a mesma classe de armadilha que [#9](https://github.com/panlabs-tech/overpower/issues/9) mediu para symlink em POSIX, replicada em junction no Windows — com um agravante que não existe em POSIX.

### 7.1 `os.path.islink()` mente, e a stdlib sabe

Medido sobre uma junction:

| Predicado | 3.10.9 | 3.12.10 |
| :--- | :--- | :--- |
| `os.path.islink()` | **False** | **False** |
| `pathlib.Path.is_symlink()` | **False** | **False** |
| `os.path.isjunction()` | não existe | **True** |
| `pathlib.Path.is_junction()` | não existe | **True** |
| `os.lstat().st_reparse_tag` | `0xa0000003` | `0xa0000003` |
| `stat.S_ISLNK(lstat.st_mode)` | False | False |
| `FILE_ATTRIBUTE_REPARSE_POINT` | True | True |

`os.readlink()` **funciona** e devolve `\\?\C:\...` — com prefixo de dispositivo, diferente do que `os.symlink` devolveria.

`os.path.isjunction()` e `Path.is_junction()` entraram na **3.12**. Como o piso do projeto é `>=3.12`, o overpower tem o predicado certo disponível e **não precisa** do check manual de `st_reparse_tag`.

### 7.2 …mas `shutil.rmtree()` recusa a junction assim mesmo

```python
>>> os.path.islink(junc)
False
>>> shutil.rmtree(junc)
OSError: Cannot call rmtree on a symbolic link
```

Não é bug: é deliberado. `Lib/shutil.py` na `v3.12.10` define um predicado **próprio**, só para Windows:

```python
def _rmtree_islink(path):
    st = os.lstat(path)
    return (stat.S_ISLNK(st.st_mode) or
        (st.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
         and st.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT))
```

A consequência para o código do overpower é direta e não óbvia. **Este padrão, que é o idiomático, quebra:**

```python
if os.path.islink(p):      # ← False para junction
    p.unlink()
else:
    shutil.rmtree(p)       # ← OSError: Cannot call rmtree on a symbolic link
```

O predicado a usar é `os.path.isjunction(p) or os.path.islink(p)`.

### 7.3 `rmtree(ignore_errors=True)` não remove e não avisa

Exatamente o modo de falha que [#9](https://github.com/panlabs-tech/overpower/issues/9) mediu para symlink em POSIX, agora medido para junction no Windows:

| Operação | Junction removida? | Alvo preservado? |
| :--- | :--- | :--- |
| `os.rmdir(junc)` | **sim** | sim |
| `os.unlink(junc)` | **sim** | sim |
| `pathlib.Path(junc).unlink()` | **sim** | sim |
| `shutil.rmtree(junc)` | não — levanta | sim |
| `shutil.rmtree(junc, ignore_errors=True)` | **não — e silencioso** | sim |
| `shutil.rmtree(pai_que_contem_junc)` | sim | **sim** — não atravessa |

A linha perigosa é a quinta. A junction **sobrevive**, sem exceção e sem retorno de erro. E como escrita através de uma junction **atinge o alvo** — medido, um arquivo criado em `junc/` aparece em `canon/` — um `copytree` logo depois escreve **através** dela e **corrompe o canônico** em `~/.agents/skills`. É a sequência `rmtree(ignore_errors=True)` → `copytree` que [#9](https://github.com/panlabs-tech/overpower/issues/9) já proibiu para POSIX; ela é igualmente proibida no Windows, pela mesma razão.

Duas boas notícias medidas: `os.unlink` e `Path.unlink` **funcionam** sobre uma junction (incomum — `unlink` normalmente não remove diretório no Windows), e `shutil.rmtree` sobre um **pai** que contém uma junction **não atravessa** — o alvo externo sobreviveu íntegro.

### 7.4 `CreateJunction` aceita um arquivo como alvo e cria lixo

```
src = <arquivo>  →  CreateJunction: ok (sem exceção)
   j-file existe : True
   j-file isdir  : False
   listdir       : NotADirectoryError [WinError 267] The directory name is invalid
```

A validação do passo 4 (§2.5) checa **existência**, não **tipo**. Junction para arquivo não é representável, e o resultado é uma entrada inutilizável criada em silêncio. **A checagem `src.is_dir()` é responsabilidade do overpower** — o único ponto em que a API privada precisa de guarda que o `ctypes` da §4 já traz embutida.

---

## 8. Como testar código que só existe no Windows, desenvolvendo em WSL2

### 8.1 A máquina do dev **é** o ambiente corporativo

O achado que reordena esta pergunta: a máquina Windows sob este WSL2 está **sem Developer Mode, sem elevação e sem `SeCreateSymbolicLinkPrivilege`** (§1). É a configuração exata que a junction existe para servir. Não precisa ser simulada — está ali.

### 8.2 O interop do WSL2 fecha o laço, e foi medido

`pytest` do **Windows** rodando contra o repositório que vive no **WSL**, invocado do shell do WSL, sem copiar nada:

```
$ /mnt/c/.../Python312/python.exe -m pytest \
    '\\wsl.localhost\Ubuntu-20.04\home\paninit\...\test_junction.py' -v

test_junction.py::test_create_junction_sem_privilegio PASSED [ 33%]
test_junction.py::test_symlink_falha_sem_privilegio    PASSED [ 66%]
test_junction.py::test_rmtree_recusa_junction          PASSED [100%]
============================== 3 passed in 5.34s ==============================
```

Três peças que tornam isso viável, todas verificadas:

- O Python do Windows **enxerga o repo do WSL** por UNC `\\wsl.localhost\<distro>\...` — `os.listdir` funcionou.
- `pytest` e `uv` **já estão instalados** no Python 3.12 do Windows desta máquina.
- **Latência aceitável**: 0,42 s por invocação do Python do Windows a partir do WSL, contra 0,019 s do Python nativo do WSL. ~22× mais lento, absolutamente irrelevante num alvo de teste que roda sob demanda.

Custo de infraestrutura: **zero**. Nenhuma VM, nenhum container, nenhum runner.

Ressalva medida: quando o `cwd` é UNC, o `cmd.exe` reclama em `stderr` (§3.3). Não afeta o `pytest`, mas afeta qualquer teste que dispare `cmd`.

### 8.3 O que a CI do GitHub **não** consegue testar

Lido no `actions/runner-images`, fonte primária:

- `images/windows/scripts/build/Configure-DeveloperMode.ps1` grava `AllowDevelopmentWithoutDevLicense = 1` (DWORD) em `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock`. O script **é invocado** em `images/windows/templates/build.windows-2025.pkr.hcl` (linha 201).
- O mesmo template faz `net localgroup Administrators ${var.install_user} /add` (linha 44) e **verifica** a filiação (linha 51).
- `Configure-BaseImage.ps1` grava `ConsentPromptBehaviorAdmin`; um mantenedor do runner-images afirma na [discussão #6557](https://github.com/actions/runner-images/discussions/6557): *"UAC is disabled by default on Windows images."*

Conclusão: no `windows-latest`, **Developer Mode está ligado, o usuário é administrador e o UAC está desligado**. Logo `os.symlink` **funciona** lá.

Consequência prática, e é dura: **a CI do GitHub não reproduz o `WinError 1314`.** O teste `test_symlink_falha_sem_privilegio` que **passa** na máquina do dev **falharia** no `windows-latest`. Um teste que afirme "sem privilégio, o symlink falha" não pode ser escrito contra a CI hospedada.

### 8.4 As camadas de teste que decorrem disso

1. **Independente de plataforma** (roda em WSL, roda na CI Linux — a maioria): a montagem de argumentos, a validação `is_dir()`, a escolha do degrau, a mensagem de degradação. Com `_winapi.CreateJunction` **injetada como porta** e substituída por um fake, o ramo de fallback é exercitável em qualquer SO. Este é o argumento de forma que casa com o `panlabs-python-standards`: a chamada ao SO fica atrás de uma porta estreita, e a política acima dela é testada sem SO nenhum.
2. **`windows-latest` na CI** (`pytest.mark.skipif(sys.platform != "win32")`): que `CreateJunction` existe, cria, resolve e é removível pelo predicado certo. Vale porque cobre a matriz de versões de Python — o que a máquina do dev não faz.
3. **Máquina do dev, sob demanda, via interop** (§8.2): o único lugar onde o **caso sem privilégio** é observável. Não é portão de CI; é verificação manual antes de release, e deve estar documentada como tal.

O ponto a internalizar: a camada 3 não é substituível pela 2. Se o overpower quiser um portão automático para o caso sem privilégio, precisa de um runner **self-hosted** não elevado — custo que a v0.1.0 não deve pagar, dado que **a junction não depende de privilégio de todo modo** (§6) e o ramo em questão é o de cópia, que a camada 1 já cobre com o fake.

---

## 9. Recomendação

1. **Usar `_winapi.CreateJunction`.** Uma linha, presente desde a 3.5.0, documentada na tabela de audit events, sustentada por cinco módulos de teste da stdlib.
2. **Isolar a chamada atrás de uma porta estreita** — um módulo com a única função que toca `_winapi`. Compra as três coisas ao mesmo tempo: o ponto único onde o `hasattr` defensivo vive, a fronteira onde `Path` vira `str` (§2.6), e a costura que torna o fallback testável em Linux (§8.4, camada 1).
3. **Validar `src.is_dir()` antes de chamar** (§7.4).
4. **`except Exception` largo em volta da chamada**, caindo para cópia — não `except OSError`. Um audit hook (§2.3) não levanta `OSError`.
5. **Não rodar o probe de symlink no Windows** (§6). Junction primeiro, cópia se falhar.
6. **Remover junction com `os.path.isjunction(p) or os.path.islink(p)` → `unlink()`**, nunca com `shutil.rmtree`, e **jamais** com `rmtree(ignore_errors=True)` (§7.2, §7.3).
7. **Registrar a saída `ctypes` como contingência** neste documento (§4). Não implementar agora.
8. **Documentar a verificação manual via interop do WSL2** (§8.2) como passo de release, e registrar que a CI hospedada não cobre o caso sem privilégio (§8.3).

---

## 10. Perguntas que esta pesquisa deixa em aberto

- **Junction entre volumes locais distintos.** A doc da Microsoft afirma que funciona; não foi possível medir — esta máquina só tem `C:`. O caso real é `~/.agents` em `C:` e um repo em `D:`, plausível numa estação com SSD + HDD.
- **Junction com alvo em share SMB.** §6 conclui pela doc que não serve. Não medido; sem share disponível.
- **Junction em ReFS.** Reparse points existem; comportamento não medido.
- **`AdjustTokenPrivileges` sob política corporativa restritiva.** Nesta máquina o passo 3 (§2.5) é inócuo porque o privilégio não é detido. Em máquina com AppLocker ou hardening agressivo, se `OpenProcessToken` falhar, a função aborta — não medido, e não há como medir sem uma máquina gerenciada por domínio.
- **Windows ARM64.** Todas as medições em x64 (`MSC v.1943 64 bit (AMD64)`).
- **Comportamento de `git status` diante de uma junction** dentro de um repo. Fora do escopo desta pergunta — em modo projeto a decisão 6 do [#9](https://github.com/panlabs-tech/overpower/issues/9) já proíbe link — mas seria necessário se algum dia o modo projeto reabrisse.

---

## Fontes

| Fonte | O que sustenta | Consulta |
| :--- | :--- | :--- |
| `python/cpython` `Modules/_winapi.c` @ `v3.14.0` | implementação, audit event, validação de `src`, `SE_RESTORE_NAME`, comentário do `REPARSE_DATA_BUFFER` | 2026-08-01 |
| `python/cpython` `Modules/_winapi.c` @ `v3.2.6`…`v3.14.0` | função nasce na 3.5.0 | 2026-08-01 |
| `python/cpython` `PC/config.c` @ `v3.14.0` | `_winapi` é builtin incondicional | 2026-08-01 |
| `python/cpython` `Lib/shutil.py` @ `v3.12.10` | `_rmtree_islink` diverge de `os.path.islink` no Windows | 2026-08-01 |
| <https://docs.python.org/3/library/audit_events.html> | `_winapi.CreateJunction` documentada com `src_path, dst_path` | 2026-08-01 |
| `python/cpython` commit [`de4ced54e`](https://github.com/python/cpython/commit/de4ced54e) + PRs 114089/114134/114135 | fix de restauração de privilégio e backports para 3.12 e 3.11 | 2026-08-01 |
| Busca de código `python/cpython` por `CreateJunction` | 5 arquivos de teste da stdlib dependem dela | 2026-08-01 |
| Busca de código `pypy/pypy` por `CreateJunction` | 0 resultados | 2026-08-01 |
| <https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions> | junction liga diretórios em volumes **locais**; reparse points | 2026-07-30 (via [#5](https://github.com/panlabs-tech/overpower/issues/5)) |
| <https://gitforwindows.org/symbolic-links> | junction dispensa privilégio de administrador | 2026-07-30 (via [#5](https://github.com/panlabs-tech/overpower/issues/5)) |
| `actions/runner-images` `images/windows/scripts/build/Configure-DeveloperMode.ps1` | Developer Mode ligado nas imagens do GitHub | 2026-08-01 |
| `actions/runner-images` `images/windows/templates/build.windows-2025.pkr.hcl` | script invocado (l. 201); usuário em `Administrators` (l. 44, 51) | 2026-08-01 |
| [`actions/runner-images` discussão #6557](https://github.com/actions/runner-images/discussions/6557) | *"UAC is disabled by default on Windows images"* | 2026-08-01 |
| Medição: Windows 11 build 26200, não elevado, sem Developer Mode | `WinError 1314` no symlink; `CreateJunction` funciona; predicados; remoção; `mklink`; `ctypes`; latência de interop; `pytest` por UNC | 2026-08-01 |
| `vercel-labs/skills` @ `7cb7db64` `src/installer.ts:255-257` | junction direto no Windows, sem tentar symlink | 2026-07-30 (via [#5](https://github.com/panlabs-tech/overpower/issues/5)) |
