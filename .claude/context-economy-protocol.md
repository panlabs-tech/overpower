# Protocolo de economia de contexto — implementação

> Injetado pelo hook `UserPromptSubmit` quando uma implementação começa. Este
> arquivo é também o **marker** de opt-in: enquanto ele existir, os hooks de
> economia de contexto ficam ativos neste repo; sem ele, são inertes.

Você está começando a implementar. A meta é chegar ao primeiro teste RED com a
janela perto do baseline — ~35k —, não em 150k.

**Medido neste repo, 45 sessões que escreveram código:** o primeiro `Edit`
acontece com **152k tokens** de mediana. A repartição não é a intuitiva. Só ~50k
são bytes de arquivo e de comando; **~61k é o seu próprio raciocínio**, gerado
nos ~63 turnos gastos orquestrando a exploração, e ~35k é o baseline. Ler menos
corta um terço do dano. **Tirar o reconhecimento da janela corta dois terços** —
os turnos acontecem na janela do subagente, e só o digest atravessa.

## A ordem

1. **A primeira ferramenta é `Agent`.** Até o digest chegar, o reconhecimento
   inteiro é dele: a árvore, os vizinhos, os docs, a issue. No modo autônomo
   ("implementa as issues"), um `Explore` por issue. Vale seguir direto quando a
   issue nomeia o arquivo **e** a mudança cabe numa função — diga que é o caso e
   siga.

2. **Peça um digest de schema fixo**, com teto de ~2.5k tokens:
   - **arquivos relevantes** — path, e por que cada um importa;
   - **o vizinho mais próximo, verbatim** — o arquivo que o código novo vai
     espelhar: o módulo irmão, o teste irmão, o fake. O digest carrega o código a
     clonar, e por isso não custa uma segunda leitura sua. Os demais entram só
     por path;
   - **o padrão a espelhar**, e as invariantes ou ADR que se aplicam;
   - **os seams de TDD** — onde o RED encosta.

   `CLAUDE.md` tem a tabela de qual **seção** de `docs/agents/*` responde o quê.
   Mande o `Explore` pela tabela: `domain.md` tem 26k e `testing.md` 23k, e a
   seção certa custa um décimo do arquivo.

3. **Aja sobre o digest.** O vizinho que veio verbatim você clona. Dos demais,
   leia só o que o digest nomeia, e só o que faltou, em fatia estreita
   (`offset`/`limit`). O digest é o **orçamento de leitura**.

4. **Vá direto ao RED.** O digest já é o plano — escreva o teste que falha,
   deixe-o falhar, e só então o GREEN.

5. **Narre comprimido.** Como primeira ação, acione `/caveman` no modo **ultra**.
   Código, commits, corpos de PR e avisos de risco seguem em prosa normal — as
   seções *Boundaries* e *Auto-Clarity* da própria skill garantem isso; só a
   narração encolhe. Medido: 2.4k → 0.2k tokens de prosa por sessão.

6. **Issue enxuta.** Só a issue-alvo, campos nomeados:
   `gh issue view N --json title,body,labels`. Irmãs e `--comments` entram com
   necessidade real declarada.

7. **Output cru vira digest uma vez.** `.output` de subagente e dumps de
   `tool-results/` já viraram preview. Precisa do conteúdo? Re-consulte a fonte
   com pergunta dirigida — a trava de `Read` bloqueia a releitura.

## Antes de propor o merge

O detalhe mora em `docs/agents/workflow.md` § Portões; aqui fica o que se checa
com o trabalho na mão.

- [ ] Suíte **inteira** verde (`uv run pytest`), não só o arquivo tocado.
- [ ] `ruff check` e `ruff format --check` limpos — o `lefthook` cobra no commit,
      e a CI cobra de novo.
- [ ] Fragmento em `changelog.d/`, nomeado pelo número da issue.
- [ ] PR muda o wheel? O `release-ready` vermelho já calculou o nível e imprimiu
      os dois comandos — use os dele, sem decorar o nível.
- [ ] PR aberto `--draft` no primeiro push; corpo escrito no fim, por quem tem o
      ticket na mão; `gh pr ready` depois.
