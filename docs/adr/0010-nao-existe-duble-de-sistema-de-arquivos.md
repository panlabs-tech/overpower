# Não existe dublê de sistema de arquivos

O overpower é um programa que escreve arquivos. A suíte escreve arquivos **de verdade**, em `tmp_path`, sempre. Não existe `FakeFileSystem`, não existe port de filesystem, não existe `mock_open`, e nenhum teste de escrita é gateado por variável de ambiente.

Decidido em [Doutrina de teste: o que é fake, o que é real, e como testar saída visual](https://github.com/panlabs-tech/overpower/issues/30). A doutrina inteira mora em [`docs/agents/testing.md`](../agents/testing.md); esta ADR guarda só a posição que um leitor da régua vai querer desfazer.

## Por que isto precisa de ADR

A régua de forma de código deste repo é o `panlabs-python-standards`, e a primeira linha da doutrina de testes dele é uma pirâmide:

| Camada | Dublê |
| --- | --- |
| Domínio | nenhum |
| Use-case / orquestração | **fake de port, sempre** |
| Adapter | nenhum — infra real, gateada |

Quem ler essa tabela e abrir `tests/` vai encontrar **zero fakes** e concluir que faltou alguém escrever o port. Não faltou. Esta ADR existe para que a conclusão certa esteja escrita antes de alguém "consertar" o repo.

## A régua se auto-adjudica: isto não é divergência

A regra da pirâmide vem com **condição** declarada, e ela vale *"onde os três existem simultaneamente: (i) port explícito entre use-case e infra, (ii) type-checker strict gateando o merge, (iii) suíte de adapter rodando contra a infra real"*. E o texto continua: *"faltando qualquer um dos três, a regra se inverte"* — o teste contra o recurso real passa a ser o correto.

Aqui:

- **(ii) existe** — `pyright` strict é portão de PR, fixado no [#24](https://github.com/panlabs-tech/overpower/issues/24).
- **(iii) existe de forma trivial**, porque a infra é o disco e ele nunca está fora do ar.
- **(i) não existe, e não vai existir.** Não há port de filesystem.

Faltando (i), a própria régua manda testar contra o real. **Seguir a régua produz esta decisão**; ela não é vencida, é aplicada.

## O que torna (i) indesejável aqui, e não só ausente

O que um fake de filesystem compraria é o que a régua nomeia como garantia: *"uma suíte que roda offline, em segundos, sem serviço de pé"*. **Isso já é verdade sem ele.** O disco não precisa de `docker compose`, não tem matriz de versões, não cai, e `tmp_path` custa microssegundos. O fake compraria uma garantia que já se tem — e pelo portão anti-cerimônia da própria régua, custo sem garantia nova é cerimônia.

E há o custo positivo, que é o que fecha a questão. As três armadilhas de mecânica que o mapa mediu e declarou **obrigatórias** são, todas, comportamento de sistema de arquivos real:

| armadilha | medida em | por que um fake não a mostra |
| --- | --- | --- |
| `rmtree(ignore_errors=True)` sobre symlink **não remove e não avisa**, e o `copytree` seguinte escreve **através**, corrompendo o canônico | [#9](https://github.com/panlabs-tech/overpower/issues/9) | exige symlink com semântica de travessia |
| `os.path.islink()` devolve **`False`** para junction, e o `shutil.rmtree()` a recusa assim mesmo (`_rmtree_islink` próprio do Windows) | [#19](https://github.com/panlabs-tech/overpower/issues/19) | exige junction do NTFS e o `shutil` real |
| `dirs_exist_ok=True` **sobrepõe sem sincronizar** | [#9](https://github.com/panlabs-tech/overpower/issues/9) | exige a implementação real do `copytree` |

Um dublê que reproduzisse as três seria uma reimplementação do `shutil` e do NTFS — e passaria a ser o sujeito a testar. **Um fake que mente sobre exatamente os três bugs que o produto tem é pior que nenhum fake**, porque produz verde onde o real é vermelho.

## Consequences

**A suíte inteira roda nas 9 células.** Se o disco é o sujeito, a divergência entre os sistemas de arquivos é o que se está testando, e ela só aparece rodando lá. O custo é nulo: o [#24](https://github.com/panlabs-tech/overpower/issues/24) mediu overhead fixo de **7–13 s por job** contra uma bateria de **~2 s**, então dividir a suíte não compra tempo nenhum.

**Nenhum teste de escrita tem gate de ambiente.** A trava anti-skip que a régua exige (§2) existe porque um serviço pode sumir do workflow e o CI ficar **verde skipando tudo**. O disco não some. Um marcador que nunca pode skipar é ritual, e o portão anti-cerimônia o corta.

**Teste condicionado a plataforma é chaveado por `sys.platform`, nunca por variável.** É a mesma preocupação da régua — *"quem promete a infra é quem liga a exigência"* — resolvida por uma chave que **não pode ser esquecida no workflow**: no Windows os testes de junction rodam, e não há valor de ambiente capaz de silenciá-los.

**Não nascem `tests/fakes.py` nem `tests/contracts/`.** Das três casas por papel que a régua prevê fora do espelho de `src/`, só `tests/support/` se ocupa. As outras duas ficam vazias **porque não há dublê de port que possa mentir** — que é a condição literal que a régua dá para o contract test ser obrigatório. A vacuidade está registrada em [`docs/agents/testing.md`](../agents/testing.md) para não ser lida como esquecimento.

**Rede é outra coisa, e não entra aqui.** A rede *é* infra ausente, lenta e instável — o [#3](https://github.com/panlabs-tech/overpower/issues/3) mediu isso. Ela não entra em portão nenhum, pela regra da terceira ocorrência do [#24](https://github.com/panlabs-tech/overpower/issues/24). O `git`, que é subprocesso e não rede, roda de verdade contra um **remoto local**; a doutrina explica o corte.

**Esta ADR se reabre** se nascer um port de filesystem por outra razão — aterrissagem em destino que não é disco local, por exemplo —, porque aí a condição (i) da régua passa a existir e a pirâmide volta a valer como escrita.
