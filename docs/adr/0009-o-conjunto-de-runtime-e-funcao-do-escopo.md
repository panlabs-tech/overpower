# O conjunto de `--runtime` é função do escopo

`eve` e `promptscript` declaram `globalSkillsDir: undefined` no upstream. Em escopo global eles não têm para onde ir, e o overpower **não inventa caminho**.

A decisão tem três metades, e as três saem de uma frase só — *o conjunto que `--runtime` aceita depende do escopo*:

> Em **projeto** o conjunto tem **76** membros; em **global**, **74**.
> Pedir um dos dois em global é **invocação válida com resposta negativa**: **exit 3**, e o **comando inteiro é recusado antes de qualquer escrita**.
> A tela **não oferece** os dois em escopo global.

Decidido em [Runtime sem caminho global em escopo global: recusa, pulo ou exit code](https://github.com/panlabs-tech/overpower/issues/29). A tabela e o `None` que a dispara vieram de [Tabela de caminhos de runtime](https://github.com/panlabs-tech/overpower/issues/27).

## A régua dos códigos, agora completa

A [Busca remota](https://github.com/panlabs-tech/overpower/issues/25) já tinha estreitado a régua do [#8](https://github.com/panlabs-tech/overpower/issues/8) para o caso dela. Esta decisão a fecha para o produto inteiro:

| código | significado | caso canônico |
| --- | --- | --- |
| **1** | comecei e falhei **no meio** | escrita interrompida; obtenção de `--from` falhou |
| **2** | a invocação está **incompleta ou fora da gramática** | escopo fora de repo git sem `--project`/`--global`; `--runtime` que não existe na tabela; `--runtime` ausente sem TTY |
| **3** | a invocação está **correta**, rodei, e a **resposta é não** | `--from` obteve, procurou, a skill não está lá; `--runtime eve --global` |

O eixo que separa **2** de **3** é *de quem é o defeito*: no 2 é do que foi digitado, no 3 é do mundo.

## Considered Options

### Exit 2, tratando o par como valor inválido

A leitura era construir *"o conjunto válido de `--runtime` é função do escopo, logo em global `eve` é valor inválido, logo exit 2"* — reusando o precedente que o [#8](https://github.com/panlabs-tech/overpower/issues/8) já aplicou a `--runtime` inexistente, sem inventar semântica nova. **Perdeu por duas razões, e nenhuma é de gosto.**

**Os dois precedentes de 2 falam da invocação, não do mundo.** Escopo fora de repo git sai 2 porque falta informação que só o usuário tem — *"tem de ser explícito"*, nas palavras da [ADR 0008](0008-a-tela-e-herdada-a-escrita-nao.md). `--runtime` inexistente sai 2 porque o texto não corresponde a nada. `--runtime eve --global` não é nenhum dos dois: o valor existe, a flag existe, nada falta. O que não existe é o **destino**, e destino é fato da tabela, não da linha de comando.

**E o mesmo fato voltaria como 3 pelo `doctor`.** `doctor --runtime eve --global` roda, consulta a tabela e responde *"não há nada aqui para checar"* — que é literalmente *"rodei, e a resposta é não"*. Um fato com dois códigos conforme o comando que pergunta é a ambiguidade que o #8 gastou o ticket inteiro removendo, e ela quebraria justamente o uso que o 3 existe para servir: `--dry-run` e `doctor` como portão de CI.

*Registrado porque foi a primeira leitura e não sobreviveu:* o argumento de que *"regra que não cabe no `--help` não é erro de uso"* foi levantado contra o exit 2 e **descartado** — a lista de `--runtime` já é dado que um refresh muda, então ser dado não desqualifica nada. O que desqualifica o 2 é a incoerência com o `doctor`.

### Escrever o que tem destino, reportar o resto

`--runtime eve,claude-code --global` escreveria o Claude Code, reportaria o `eve` em voz alta e sairia diferente de zero — sem nenhuma das duas metades do defeito medido no `npx skills`, que eram o **silêncio** e o **exit 0**.

**Perdeu porque a tolerância do [#9](https://github.com/panlabs-tech/overpower/issues/9) a estado parcial é condicionada, e a condição não vale aqui.** O *"falha no meio deixa e reporta, exit 1"* existe porque a falha é **descoberta no meio**, e desfazer exigiria escrever — `os.replace` sobre diretório não vazio dá `ENOTEMPTY`, e staging atômico de diretório não existe. Este caso é detectável **antes do primeiro byte**: `resolve_global_dir` devolve `None` sem tocar o disco. Recusar custa **zero estado em disco e uma edição de linha de comando**; importar a tolerância sem a causa é pagar o preço sem comprar nada.

E o parcial precisaria de um **quarto significado** de código de saída — *"parte aconteceu"* —, que é exatamente o que o #8 gastou o ticket para não ter.

### Só filtrar a tela

Filtrar resolve o caminho interativo e **não** resolve `--runtime eve --global` digitado à mão ou vindo de script. É metade necessária, não alternativa — e por isso entrou junto, não no lugar.

## O que a [ADR 0008](0008-a-tela-e-herdada-a-escrita-nao.md) já dizia, e esta é a outra metade

*"Runtime nomeado é runtime equipado"* foi escrita contra o pulo silencioso do `npx skills`, em que `.devin/` **era anunciado** e não escrito. A própria ADR 0008 explicou por que aquele caso não era exit 3:

> O `exit 3` do [#8] é *"rodei, e a resposta é não"*, e não é este caso: **aqui a resposta é sim e o alvo foi nomeado**.

Aqui a resposta é **não** e **não há alvo**. A frase da ADR 0008 delimitou o negativo; esta decisão o ocupa. A regra sobrevive intacta porque ela **quantifica sobre runtimes que têm onde ser equipados** — não se pode equipar quem não lê de lugar nenhum, e o overpower nunca aceita um contrato que não pode cumprir.

## Consequences

**A tela tem 74 linhas em escopo global.** O [#18](https://github.com/panlabs-tech/overpower/issues/18) fixou a ordem **artefatos → escopo → runtimes → confirmação**, então o escopo já é conhecido quando a lista renderiza. Oferecer `eve` ali seria oferecer o que o passo seguinte recusa — uma tela que mente sobre o que é tomável, que é a classe que a ADR 0008 existe para recusar. O custo declarado é que a mesma lista muda de tamanho conforme o escopo; ele é **honesto**, porque o conjunto de fato depende do escopo, e é invisível na prática — ninguém conta 76 contra 74.

Note a simetria com o upstream: o `npx skills` **tem** as duas linhas e não escreve nada para elas. Filtrar é o anti-pulo-silencioso aplicado à tela.

**Uma implementação só, `runtimes_in(scope)`.** A tela e o validador consomem a mesma função. Duas implementações da mesma regra divergirem é precisamente o modo de falha que a ADR 0008 documenta com três medições; aqui ele fica fechado por construção, não por disciplina.

**Em projeto a regra é inerte.** As 76 linhas têm caminho de projeto, então `runtimes_in(Scope.PROJECT)` é a tabela inteira e nenhum caminho novo nasce.

**A mensagem tem de nomear o par e a saída.** O custo aceito é que duas linhas de 76 vetam um comando sobre as outras 74; o que o torna aceitável é o erro dizer qual runtime, por quê e qual é o conserto — *instalar no repositório em vez da máquina*. Recusa sem conserto nomeado seria trocar um defeito por outro. Esse custo é do **eixo de escopo** — `RuntimeUnavailableInScopeError`, um runtime sem destino de nenhuma classe no escopo pedido — e continua vetando a linha inteira; nada aqui mudou.

**Nota ([#100](https://github.com/panlabs-tech/overpower/issues/100)):** esta leitura foi emprestada por `NoMcpDocumentError` para um **segundo eixo** — classe, não escopo — quando a [ADR 0017](0017-o-eixo-de-enxerto-tem-tabela-propria-de-runtime.md) nasceu. Nessa emenda, o eixo de classe deixou de vetar a linha inteira numa linha mista: um runtime com linha numa das duas classes não é mais varrido pelo gap na outra. Isso não pediu recusa nova — a **união** que este parágrafo já reserva ao eixo de escopo (*"um runtime sem destino de nenhuma classe"*) é exatamente a garantia que faz o eixo de classe dispensar uma: `_selected_runtimes` já recusou, por escopo, todo runtime sem linha em nenhuma das duas tabelas, então quem sobra para o eixo de classe checar tem, no mínimo, uma. O que esta ADR decide — a **escopo** é função do par (runtime, escopo), e onde a união das duas tabelas não alcança, a linha inteira morre — continua de pé e sem emenda; só o empréstimo em ADR 0017 mudou de forma.

**O número 74 é vendorizado como o 76.** Ele vem do upstream e envelhece com ele; pela **regra 5** a versão do overpower é a versão da tabela. Um refresh que dê destino global ao `eve` muda o número e não muda esta decisão.

**Esta ADR se reabre** se a tabela deixar de ter linha sem destino global — aí ela vira letra morta —, ou se a escotilha `--dir` entrar na v0.2, porque aí passa a existir um destino que o **usuário** fornece, e a recusa ganha uma terceira saída que hoje não existe: *"não sei onde, mas você pode dizer"*.
