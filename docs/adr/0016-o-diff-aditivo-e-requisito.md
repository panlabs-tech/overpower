# O diff aditivo é requisito, e a dependência que ele custa

Enxertar preserva byte a byte o arquivo do usuário: o `git diff` mostra **só** as linhas que o overpower escreveu. Isso custa uma dependência de inserção cirúrgica, e ela entra.

> `json.dumps` está proibido como escritor de enxerto.

Decidido na sessão de grilling que produziu a spec de MCP, fechando [Preservação de formato ao enxertar](https://github.com/ThiagoPanini/overpower/issues/22).

## A razão é o axioma 2, e ela não é estética

*"Num repo git, o git é o manifesto"* só vale se o diff responder **exatamente** o que a ferramenta escreveu. Medido em [Formatos de configuração de MCP por runtime](https://github.com/ThiagoPanini/overpower/issues/17), escrever com `json.dumps` no melhor caso possível — `.mcp.json` estrito, sem comentários, `indent=2` idêntico ao do usuário — já produz isto ao instalar **um** servidor:

```diff
     "antigo": {
       "command": "node",
-      "args": ["server.js"]
+      "args": [
+        "server.js"
+      ]
+    },
+    "git": { … }
```

O `antigo` é servidor do usuário e ninguém o tocou. O manifesto passou a mentir no primeiro install.

Em JSONC é pior: um `.vscode/mcp.json` de 13 linhas sai com **31**, comentários destruídos, tabs virados espaços.

## O leitor já era obrigatório

Isto não é uma dependência tomada por capricho de qualidade: **a stdlib não lê o alvo**. `json.loads` sobre `.vscode/mcp.json` com um comentário estoura `JSONDecodeError`. Com o VS Code entre os alvos, um parser tolerante a JSONC é requisito de leitura. A decisão real foi só se ele **também escreve**.

## Considered Options

### Ler com parser tolerante e escrever com `json.dumps`

O argumento honesto a favor: **as ferramentas nativas são piores**. Medido — o VS Code faz `JSON.stringify(…, '\t')` e destrói comentários; o Claude Code apaga chaves raiz desconhecidas (`$schema` some sem aviso); o Codex apaga comentários de servidores que não tocou; o Copilot reserializa tudo. Um gerador com `json.dumps` não seria pior que o comportamento nativo.

**Perdeu porque o overpower tem um requisito que eles não têm**, e é o axioma 2. *"Não somos piores que o nativo"* é régua de outro produto.

E há um custo medido extra: o trust de `.vscode/mcp.json` é `TrustedOnNonce`, com o nonce sobre o hash do launch. Reescrever o arquivo faz o usuário **reaprovar todo servidor, toda vez**.

### Escrever nosso próprio splice

Leitor JSONC mínimo mais inserção textual nossa, zero dependência. Coerente com um projeto que se fixou enxuto ([#2](https://github.com/ThiagoPanini/overpower/issues/2)).

**Perdeu por proporção**: é código de parser em produção, exercitado sobre arquivo de terceiro que pode chegar de qualquer forma, para economizar uma dependência que já era necessária como leitor.

## Consequences

**Duas armadilhas medidas viram conhecimento obrigatório de quem mexer no escritor.** A API óbvia do `json-five` — `obj.key_value_pairs.append(kvp)` — **falha em silêncio**: exit 0, nenhuma exceção, saída byte-idêntica à entrada, enxerto sumiu. A causa está no fonte: `key_value_pairs` é `@property` que reconstrói a lista a cada acesso, e o `.append()` muta um descartável. A API correta (`obj.keys.append` + `obj.values.append`) funciona e insere **sem formatação nenhuma, tudo numa linha** — formatar exige autorar os nós de whitespace à mão.

A primeira delas é exatamente a classe de defeito que este produto existe para não cometer, e ela mora **dentro** da dependência que compramos para evitá-la. O teste que a pega não é de unidade sobre o escritor: é assertar o **conteúdo do arquivo** depois da escrita.

**Colisão de nome de módulo.** O pacote PyPI `json-five` instala o módulo `json5` — mesmo nome do pacote PyPI `json5`. Os dois no mesmo ambiente é colisão.

**O `pyright` strict tem ponto cego aqui.** Medido no [estado da arte](https://github.com/ThiagoPanini/overpower/issues/2): `Any` explícito não é `Unknown`, e o escritor de enxerto é justamente código que lê JSON de terceiro. A tipagem não cobre este módulo; o teste sobre bytes cobre.

**E se o arquivo do usuário já estiver quebrado**, o overpower faz o que as CLIs oficiais fazem — medido: `claude mcp add` e `codex mcp add` **recusam e não reparam**. Reparar é editar por conta própria um arquivo que não é nosso.

**Esta ADR se reabre** se o Codex entrar como alvo: ali o formato é TOML, `tomllib` **não escreve**, e a medição mostrou `tomlkit` como o único caminho com diff aditivo — `tomli-w` apagou três comentários e refluiu um array intocado. Seria uma segunda dependência, pela mesma razão desta.
