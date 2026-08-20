# O bump é ato do autor, e o portão é quem o ensina

Publicar continua sendo mergear — a decisão do [#24](https://github.com/ThiagoPanini/overpower/issues/24) segue de pé. O que muda é que **mover a versão deixa de ser disciplina e passa a ser portão**: um required check próprio, `release-ready`, reprova o pull request que muda o wheel sem mover a versão, e **imprime na falha o nível calculado e os dois comandos a rodar**. Nenhum bot escreve na branch, nenhuma credencial entra no repositório, e nenhuma skill de mercado é modificada.

Decidido em [Publicação automática: o bump de versão vira portão, não ato manual](https://github.com/ThiagoPanini/overpower/issues/62).

## O defeito era o silêncio, não a falta de automação

A cadeia `merge → tag → publish` já era automática e já não tinha credencial. O elo manual era um só, o `uv version --bump` que o `README.md` mandava rodar à mão — e era justamente o que decidia se a cadeia inteira rodava.

| | |
| --- | --- |
| `v0.1.0` aponta para | `66ecdeb` ([#56](https://github.com/ThiagoPanini/overpower/issues/56)) |
| merges na `main` depois disso | [#59](https://github.com/ThiagoPanini/overpower/issues/59), [#60](https://github.com/ThiagoPanini/overpower/issues/60), [#61](https://github.com/ThiagoPanini/overpower/issues/61) |
| desses, moveram a versão | **zero** |
| fragmentos pendurados em `changelog.d/` | **4** |

Nas três vezes o `tag.yml` leu a versão, achou `v0.1.0` já tagueada, escreveu `::notice::v0.1.0 is already tagged; nothing to release` e **saiu verde**. Três merges, nenhum erro em lugar nenhum, nada publicado. A falha só apareceu num `pip install --upgrade` que não trouxe nada — que é a definição da classe *sucesso carregando o conteúdo errado* que este mapa persegue desde o [#2](https://github.com/ThiagoPanini/overpower/issues/2).

Daí a forma da correção. O problema não era *"a inferência de versão erra"*; era *"ninguém deu o bump e o repositório não reclamou"*. A pergunta certa é **como isso vira impossível de esquecer**, e portão é a resposta que este repositório já usa em todo lugar — o mesmo raciocínio do `lefthook.yml`, onde o hook é o atalho e o ruleset é o portão.

## As duas travas que eliminam o bot

Antes de qualquer preferência, duas mecânicas fecham o desenho óbvio de *"um workflow calcula e commita o bump"*:

1. **O ruleset `main: PR obrigatorio e gate verde` tem lista de bypass vazia**, verificado e não inferido. Nada empurra commit na `main` sem pull request e sem `gate` verde.
2. **Push feito com `GITHUB_TOKEN` não dispara workflow nenhum** — o `tag.yml` já documenta isso e já contorna por `workflow_dispatch`. Consequência: um bot que commite o bump na branch do pull request deixa o SHA novo **sem** o check requerido, e o pull request trava para sempre em *"Expected — waiting for status to be reported"*.

Existe contorno (dispatch do `ci.yml` a partir do bot), e ele foi descartado por medição, não por gosto: **`towncrier build` é destrutivo e não é idempotente.** Ele apaga os fragmentos de `changelog.d/` e insere a seção no `CHANGELOG.md`. Um bot em `on: pull_request` roda a cada `synchronize`: no primeiro push consome os fragmentos e fecha a seção; o fragmento que o autor escrever depois — e escreve, porque o corpo do pull request é redigido no fim, por quem tem o ticket na mão — vira **segunda** seção com o mesmo número de versão, ou fica órfão. Somando o resto: um trigger novo, `actions: write`, guarda de idempotência, a reabertura da decisão do [#24](https://github.com/ThiagoPanini/overpower/issues/24) de não ter `on: pull_request`, e um `CHANGELOG.md` que corrompe em silêncio.

## Por que a versão não nasce na tag

A alternativa sem commit nenhum era o `tag.yml` calcular a próxima versão a partir da última tag e o `release.yml` escrevê-la **só no runner**. Ela cai porque cobra o preço que o `pyproject.toml` já recusou uma vez: o literal deixa de ser verdade, `uv version --short` passa a mentir na máquina do dev, o guard *tag == versão do pyproject* perde sujeito, e o `CHANGELOG.md` sai do arquivo para o corpo do GitHub Release. É a mesma classe do `hatch-vcs` medido no [#2](https://github.com/ThiagoPanini/overpower/issues/2) — a versão construída não é visível na árvore que a produziu.

## `release-ready` é check próprio, e não um passo do `gate`

O `gate` foi construído de propósito e o seu nome significa *"o código está são"*. Um passo de versão dentro dele deixaria o pull request vermelho do primeiro push do draft até o commit final, e as duas falhas — *conserte o código* e *bumpe a versão* — chegariam pelo mesmo nome, com remédios diferentes. Um nome por remédio é o que faz um agente autônomo acertar na primeira leitura.

O custo é uma entrada a mais no ruleset e a regra que este repositório já aprendeu do jeito difícil: **required check some por nome**, então o job tem de reportar sempre, em todo push, e nunca ser pulado. O job não usa `uv` — lê o `pyproject.toml` com `tomllib` e o resto é `git` —, então roda em paralelo com `static` e `test` e custa ~0 de wall-clock.

## O nível vem dos fragmentos, não das mensagens de commit

Havia duas fontes candidatas dentro do repositório. Venceu `changelog.d/`, por três razões e uma quarta que é de higiene:

- É **arquivo versionado**, então sobrevive intacto ao squash merge, que é o que a `main` recebe.
- Já é obrigatório na prática e já passa pelo portão.
- Sai do **mesmo artefato** que gera o `CHANGELOG.md`, logo a versão e o texto do release não têm como discordar.
- E deixa de pé o dissenso que o `lefthook.yml` registra por escrito sobre o `commitlint`: *"buys no downstream automation, because towncrier builds the changelog from fragments and never from commit messages"*. Escolher a outra fonte inverteria esse dissenso e promoveria um hook local — que aceita `--no-verify` — a decisor do que vai para o PyPI.

### O sétimo tipo, `breaking`

Keep a Changelog não tem seção de quebra, e sem ela `changed` carrega duas coisas incompatíveis: *"o banner mostra o alias"* e *"o escopo padrão virou global"* escrevem-se igual, e a segunda quebra todo mundo. A alternativa sem tipo novo era eleger `removed` como o sinal de quebra, obrigando quem muda um default a escrever *"o comportamento antigo foi removido"* — regra que mora na cabeça de quem escreve, que é exatamente a classe de falha que esta ADR existe para eliminar.

O desvio das seis seções do Keep a Changelog é assumido, e o próprio `pyproject.toml` já dava a razão ao escolhê-las: *"the output format is the decision, so the vocabulary has to be the reader's"*. **"Breaking Changes" é vocabulário do leitor**, e é a seção que um consumidor mais precisa achar — por isso é declarada primeiro e sai no topo do release.

### O mapa, e o teto do `0.x`

| tipo | em `0.x` | em `≥ 1.0` |
| --- | --- | --- |
| `breaking` · `removed` | **minor** | **major** |
| `added` · `changed` · `deprecated` | minor | minor |
| `fixed` · `security` | patch | patch |

O teto é a leitura literal do SemVer §4 — em `0.x` nada é estável, então quebra não promove. As duas alternativas caíram assim:

- **`major_on_zero`**, isto é, a primeira quebra levar o projeto a `1.0.0`, cai porque `1.0.0` é **promessa ao usuário** e não consequência de um diff. Automatizá-la faz um `fix` que por acaso quebrou algo prometer estabilidade sozinho, e no PyPI isso é irreversível. O `pyproject.toml` ainda declara `Development Status :: 3 - Alpha`.
- **A semântica de caret** — o dígito minor como fronteira de compatibilidade, `breaking` → minor e todo o resto → patch — cai porque carrega **menos** informação: `added` e `fixed` viram os dois patch, e `0.1.12` deixa de dizer se foram doze features ou doze correções. Sob a regra adotada, `0.5.1` diz *"desde a 0.5.0 só saiu correção"*. A vantagem dela, falar a semântica de `~=0.1`, vale pouco aqui, porque a invocação canônica deste produto é `uvx overpower@latest` pela **regra 5**, e não pin.

`removed` acompanha `breaking` porque, num CLI, remover algo visível **é** quebra; separá-los devolveria para a cabeça do autor a regra *"lembre de escrever também um `breaking`"*.

Ir para `1.0.0` continua sendo ato explícito: um pull request com `uv version 1.0.0` passa nas quatro asserções, porque a quarta cobra **piso** e não igualdade. Over-bump é permitido de propósito; under-bump reprova.

## O que o portão cobra, e por que ele lê o CHANGELOG

O ritual tem sempre a mesma ordem — fragmento, `uv version --bump`, `towncrier build` —, e isso cria **dois momentos** para o portão. No **momento vermelho** os fragmentos ainda existem, e é de lá que sai o nível impresso na anotação de erro. No **momento verde** o towncrier já os apagou, e sobra o `CHANGELOG.md`.

A quarta asserção lê os títulos `### …` da seção nova, e não os fragmentos via `git`, por um caso concreto: se o autor escrever o fragmento **e** rodar o towncrier no mesmo commit, o arquivo nasce e morre dentro do mesmo commit e fica invisível para qualquer `git diff` ou `git log` — a inferência daria silenciosamente *"nenhum nível"*. Ler a árvore do HEAD é imune à forma como os commits foram picados. O mapa `título → tipo → nível` não é segunda fonte: sai dos próprios blocos `[[tool.towncrier.type]]`, que já casam `name` com `directory`.

## A colisão entre pull requests não precisou de trava

Um required check é avaliado **por SHA** e não roda de novo quando a `main` anda, então dois pull requests bumpando para a mesma versão poderiam, em tese, mergear os dois com o verde do primeiro momento. Não precisam de `strict_required_status_checks_policy`, porque **o `CHANGELOG.md` já é um mutex**: o `start_string` é uma âncora única, o towncrier insere sempre imediatamente depois dela, e duas inserções concorrentes no mesmo ponto conflitam no merge. Um pull request que não bumpa não toca o arquivo e não colide com nada.

Ligar `strict` custaria caro e recorrentemente: no modo de implementação autônoma, com um worktree por issue, todo merge invalidaria os outros pull requests abertos, cada um pagando a matriz 3×3 de novo — e o update traria o `## [X.Y.Z]` da `main` para dentro de uma branch que já tem o seu, ou seja, **o mesmo conflito, agora obrigatório em toda atualização** em vez de só quando há colisão de verdade.

O que restou foi tornar o `tag.yml` alto. O predicado passou de dois ramos para três, e o terceiro é o estado em que a `main` estava:

| estado da `main` | ação |
| --- | --- |
| `v<versão>` não existe | tagueia e dispara o release |
| existe **e aponta para o HEAD** | verde e quieto — é re-run, e a idempotência era propriedade declarada |
| existe e aponta para **outro commit** | `::error::` e `exit 1` |

## Consequences

**A regra 5 deixa de ser instrução de README.** *"A versão do overpower é a versão do catálogo"* era cobrada em prosa, no passo 5 do procedimento de refresh. Agora é mecânica: `src/overpower/content/` está na lista de gatilho, então um refresh de conteúdo não mergeia sem bumpar.

**Quase todo pull request de feature vira `minor`.** Cinco dos sete tipos dão minor sob o teto do `0.x`; só `fixed`/`security` sozinhos dão patch. A versão corre rápido — `0.2.0`, `0.3.0`, `0.4.0` — e **o rótulo `v0.2` das issues do mapa diverge do número publicado**. Isso é aceito e vale dizer em voz alta: `v0.2` é rótulo de mapa, versão publicada é fato sobre um build. Fazê-los coincidir exigiria voltar a decidir versão à mão.

**Um pull request só de `docs/`, `tests/`, `.github/` ou de tabela `[tool.*]` mergeia publicando nada.** O gatilho é o **wheel**, e não o sdist — e essa distinção só existe porque foi medida: o sdist publicado é o repositório inteiro. O `overpower-0.1.0.tar.gz` do PyPI tem **164 arquivos**, com `docs/adr/` completo, `docs/agents/`, `tests/` com os snapshots, os três workflows e `.vscode/`; o wheel tem 97 entradas sob `overpower/` mais o `dist-info`. Sob a leitura do sdist, *"este pull request muda o que é publicado?"* responderia **sempre sim**, até para uma vírgula num ADR.

**O sdist inchado fica como resíduo declarado.** Como o hatchling o monta pelo `.gitignore` e não pelo que o git rastreia, um arquivo excluído apenas em `.git/info/exclude` entra no pacote — medido com `.claude/scheduled_tasks.lock`, um lock local de sessão, presente no sdist recém-construído. Consertar exige tocar em `[tool.hatch.build...]`, que a [ADR 0004](0004-build-nao-forca-inclusao-de-conteudo.md) proíbe sem prova em contrário vinda de um build de CI sobre clone limpo. **Não é decidido aqui**, e merece grilling próprio.

**Pull request de colaborador externo ficaria vermelho no `release-ready`**, porque ninguém pede a um estranho que bumpe versão. Zero ocorrências até hoje, e o `docs/agents/issue-tracker.md` já declara que PR externo não é superfície de triagem deste repositório. Declarado em vez de resolvido por especulação.

**Um ato manual, uma vez:** `release-ready` entra no ruleset **depois** de o job existir e ter reportado. A ordem é a mesma lição do [#24](https://github.com/ThiagoPanini/overpower/issues/24) — required check que ainda não publicou trava todo pull request esperando um nome que ninguém reporta.

**Esta ADR se reabre** se o GitHub passar a permitir que um push com `GITHUB_TOKEN` dispare workflow, porque aí o bot volta a ser possível e o único argumento contra ele passa a ser a destrutividade do `towncrier`, que tem conserto. Reabre também se o repositório ganhar mais de um mantenedor com pull requests concorrentes rotineiros, porque aí o mutex do `CHANGELOG.md` deixa de ser barato e vira atrito. E reabre no `1.0.0`, quando o teto do `0.x` sai e `breaking` passa a mover o primeiro dígito de verdade.
