# Um arquivo, um formato: `.overpower.yaml`

Um repositório caseiro declara **tudo o que oferece num único arquivo YAML na raiz** — `.overpower.yaml`: os bundles e as receitas de MCP, sob as chaves `bundles:` e `mcp:`. O catálogo embutido migra junto: `catalog/catalog.yaml` ganha a chave `mcp:` e as quatro receitas de `catalog/mcps/*.toml` entram nela. **O TOML sai do produto.** Achar `.overpower/mcp/<slug>.toml` num repositório que não tem `.overpower.yaml` é **exit 3**, nomeando o arquivo a escrever.

Decidido na sabatina de instalação federada de MCP, 2026-08-21.

**Substitui a [ADR 0020](0020-o-manifesto-e-yaml-e-a-receita-ao-lado-nao.md)**, de quatro dias antes.

## O que mudou desde a 0020

A 0020 decidiu com uma premissa que era verdade quando ela foi escrita: *"a receita é contrato de chave fechada, onde a única-forma-de-escrever do TOML é feature; **o manifesto tem dois campos**"*. Duas coisas tiraram essa premissa do lugar.

**O manifesto deixou de ter dois campos.** Com o servidor MCP entrando em `items` ([ADR 0022](0022-servidor-mcp-e-artefato.md)), o arquivo deixa de ser uma tabela de bundles e passa a ser a declaração inteira do que o repositório oferece. Ele e a receita respondem à mesma pergunta, e a 0020 já dizia que o que desempata é *"qual arquivo é o irmão do manifesto"*.

**O custo do corte foi medido, e quem pagou foi o publicador.** O `panlabs-skills` é o primeiro repositório real a federar: **três arquivos, dois formatos, um namespace**, e **zero linha do produto** que ensine qualquer um dos dois endereços. A 0020 registrou que `.overpower/mcp/<slug>.toml` tem *"zero ocorrências no README"* como argumento de que a base instalada não travava a decisão; a mesma medição, vista do lado de quem escreve, diz que a convenção não é descobrível de jeito nenhum.

## Considered Options

**`.overpower.yaml` na raiz era a alternativa da própria 0020**, e lá perdeu *"para a simetria de nome: um autor que abrir o wheel encontra `catalog.yaml` com o mesmo schema que ele escreveu"*. A simetria que paga é a de **schema e leitor**, e ela sobrevive inteira — um schema, um decodificador, os dois lados. A simetria de **nome** não sobrevive, e é deliberado: um dotfile como recurso de pacote é risco de empacotamento neste repositório especificamente, onde `ignore-vcs = true` já vazou um `.env` para o sdist publicado ([ADR 0004](0004-build-nao-forca-inclusao-de-conteudo.md)).

**Manter pasta no embutido e arquivo único no federado** daria mesmo schema com dois layouts, e um leitor com dois modos — a forma fraca de *"dois leitores para um schema"*, que é o que este repositório recusou por escrito duas vezes.

**Aceitar as duas formas dos dois lados**, mesclando `.overpower.yaml` com `.overpower/mcp/<slug>.yaml` ao lado, custa uma regra de colisão para nome que aparece nos dois lugares — vocabulário novo comprado para resolver um problema que só existe porque as duas formas foram admitidas.

**Uma chave `version: 1` na raiz** foi considerada e recusada: é campo que só serve na segunda versão do schema, e até lá é ruído que todo publicador copia sem saber por quê. A allowlist fechada de chaves já recusa por nome o que não conhece, e dá a mensagem melhor — ela nomeia **qual** chave não existe.

## Consequences

**A declaração é ancorada na raiz, e o alcance não.** `--from .../tree/<ref>/<subpasta>` deixa de poder carregar declaração própria: o `.overpower.yaml` é lido na raiz do repositório obtido, como o `catalog.yaml` federado já era. A subpasta continua sendo raiz de busca para **skill**, que se descobre andando — é a [ADR 0019](0019-a-vitrine-e-ancorada-o-alcance-nao.md) inalterada, agora com a declaração do lado ancorado.

**A única-forma-de-escrever se perde, e não ganha mecanismo.** `slots: [{name: X, role: env}]` e a mesma coisa em bloco são o mesmo documento para qualquer parser. O leitor trabalha sobre a árvore parseada e **aceita qualquer YAML válido**; bloco é a convenção da casa e não tem trava. É a regra 43 do padrão panlabs — *sem mecanismo, confere-se em review* — e aqui nem review existe, porque o arquivo é do publicador. Recusar grafia de fluxo custaria um segundo parser, já que `yaml.safe_load` devolve árvore e não posições, para comprar uniformidade cosmética em repositório alheio.

**As 855 linhas de `recipes.py` não morrem: mudam de entrada.** A validação é de **contrato**, não de sintaxe — allowlist fechada de chaves, transporte, papéis de slot, precondições, fonte —, e ela roda sobre a árvore parseada tanto vinda de TOML quanto de YAML. O que sai é o decodificador de TOML; a promessa *"a recipe that gets past this module is a recipe that renders"* continua de pé, e continua sendo um validador só para as duas procedências.

**A recusa do TOML nomeia o conserto.** Como toda saída 3 deste produto: diz qual arquivo foi achado, que o formato saiu, e qual arquivo escrever no lugar. O parque instalado no dia da decisão são **dois arquivos untracked** num repositório que ainda não tem um commit, o que é o que dispensa janela de compatibilidade — ela custaria dois leitores para um schema pelo tempo que durasse.
