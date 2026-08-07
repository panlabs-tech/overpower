# A régua de adjudicação — como uma posição entra, se defende e cai

Este arquivo não contém posição técnica nenhuma. Ele contém o **dispositivo de auto-vínculo** que governou todas as outras: o que conta como razão pra incluir um padrão, que tipo de evidência decide que tipo de alegação, e o que se registra quando uma alternativa perde.

Leia antes de propor mudança em qualquer posição. Uma proposta que não passa por aqui não é discordância — é preferência sem lastro, e a régua tem nome pra isso.

> A régua se aplica a si mesma. Se qualquer parte dela for ritual que não amarra garantia, corta também.

## 1. Default — excluir por default

Todo padrão está **fora** até que um cenário concreto o justifique. "É best practice reconhecida" não é razão; o cenário é.

O escopo do cenário é amplo — vale um projeto vivo, um projeto do portfólio, um projeto futuro genuinamente previsto, ou um modo de falha **demonstrado** nas codebases estudadas. O que não vale é o padrão existir porque alguém respeitável o publicou.

A consequência de forma importa mais que a regra: isso produz posições **condicionais** — regra *mais* o predicado de quando ela se aplica. É essa forma que porta entre projetos heterogêneos, e é por isso que praticamente toda posição desta referência tem um bloco `CONDIÇÃO`. Uma regra incondicional ou é trivial ou está escondendo o cenário que a justifica.

## 2. Laboratório — pedagogia é método, não conteúdo

Construir o padrão argumentando cada eixo contra evidência **é** o exercício sênior. Isso é *como* se constrói, não licença pra incluir pattern sem justificar.

"Garantia" conta cenários de **escala, consistência e portabilidade** — "passando de N módulos, a ausência disto custa X" é argumento legítimo e completo. Por isso a referência fica tão rica quanto uma base de expert de verdade. O que ela não carrega é a cerimônia que os próprios experts recusam: se as codebases de produção estudadas omitem um pattern universalmente, praticá-lo afasta do alvo em vez de aproximar.

## 3. Classes de evidência — por tipo de alegação

O erro mais comum em discussão de padrão é usar evidência da classe errada. A régua separa quatro:

| Classe de alegação | O que decide | O que não decide |
|---|---|---|
| **Comportamento** — o que a ferramenta faz | **Experimento** contra as versões pinadas. Fonte primária confirma. | Opinião não entra, nem doc oficial sozinha. |
| **Definição** — o que um pattern é ou promete | Fonte primária dona: spec, PEP, artigo original. | Decide o *significado*, nunca o *uso*. |
| **Norma** — devemos usar isto aqui | Portão de garantia (§1–2) + empírico de produção. | **O artigo original é autoridade definitional, nunca normativa** — não justifica inclusão sozinho. |
| **Opinião** — livro, blog, skill de terceiro | Levanta hipótese. Desempata fraco só quando primária e empírica são ambas silenciosas. | Nunca decide. |

Dois desempates que operam em cima disso:

- **Realidade medida acima de promessa documentada.** Doc que diz o que a ferramenta deveria fazer perde pra experimento que mostra o que ela faz. Isto já derrubou alegações de fontes primárias durante as adjudicações.
- **Empírico só é dispositivo em consenso.** Consenso ~universal entre as codebases estudadas decide. Fora do consenso, o empírico rebaixa a informativo: mapeia o espaço de opções, não escolhe.

Corolário prático: quando o consenso empírico aponta **contra** a posição que se quer defender, a saída honesta não é descartar a evidência — é transformá-la no **antecedente de uma regra condicional**, de modo que os dois mundos fiquem cobertos. Foi assim que "o erro carrega o status HTTP", praticado por 6 de 6 backends estudados, sobreviveu como norma pra projeto de borda única sem se impor a projeto com segunda borda.

## 4. O papel do autor — sem "conforto"

**O termo "conforto" sai do vocabulário.** Ele é o disfarce mais comum de posição sem lastro, porque não é falsificável.

Os insumos legítimos de decisão são quatro: **primária, empírica, experimento e garantia** — e "garantia" embute ergonomia, consistência e portabilidade, todas nomeáveis.

Daí três desfechos possíveis, e só três:

1. **Preferência nomeável** — dá pra dizer o que ela compra em palavras verificáveis. Então é garantia, e decide no mérito. Nunca foi conforto.
2. **Empate verdadeiro** — nada nomeável distingue as opções. Então a escolha é **explicitamente arbitrária** e vai rotulada como tal ("qualquer uma serve, escolhi esta"), sem fingir princípio. Rótulo de empate é honestidade barata; princípio fabricado é dívida cara.
3. **Override da evidência decisiva** — permitido, com rótulo brutal: *"desvio da evidência, sem lastro, por escolha de autor"*, custo declarado, registrado no dissenso. E sob **orçamento de cerimônia**: se o autor sobrepõe eixo após eixo, isso mesmo vira gatilho de reabertura da régua inteira.

O caso mais instrutivo de aplicação disto foi uma auto-correção: a vantagem da forma-função do use-case ("assinatura é contrato completo, sem estado escondido") tinha sido apresentada como garantia dura e **caiu pra preferência nomeável** sob pressão, porque um `frozen=True` na alternativa já matava o risco de estado mutável. A posição sobreviveu; a justificativa foi rebaixada. É isso que "a régua se aplica a si mesma" significa na prática.

## 5. Registro de dissenso

Toda posição carrega quatro partes, **inline junto da posição**, nunca num apêndice de dissenso:

1. **A vice** — a alternativa que ficou em segundo lugar.
2. **O steelman dela** — a evidência mais forte a favor, escrita honestamente. Se não dá pra escrever, ou não houve rival vivo, ou o eixo não foi entendido. Não há terceira hipótese.
3. **Por que perdeu.**
4. **O gatilho de reabertura** — a mudança concreta de versão, contexto ou evidência que a ressuscita.

**Serviço duplo:** no override de autor (§4), o registro inverte — a evidência desafiada fica registrada como a minoria vencida, com nome e argumento.

Onde não houve rival, escreve-se **"sem rival — evidência unânime"** e pronto. Fabricar uma vice pra preencher o formulário é a cerimônia que a própria régua corta.

O gatilho é a parte que mais trabalha no longo prazo. Ele converte a referência de dogma em contrato com validade: quem discorda não precisa reabrir a discussão inteira, precisa mostrar que o gatilho disparou.

## 6. O portão anti-cerimônia

Três checagens, e toda posição passa pelas três.

### 6.1 Cenário nomeado, nos dois sentidos

Incluir **e** excluir precisam nomear a falha concreta e onde ela é evidenciada.

"Clean Architecture manda fazer" e "minimalismo manda não fazer" são **igualmente** cerimônia. Esta checagem existe pra impedir que a régua vire minimalismo por esporte — o que seria só trocar um dogma por outro. Por isso posições como "pydantic é legítimo na borda" existem: barrá-lo do núcleo tem cenário, barrá-lo da borda não tem.

### 6.2 Garantia verificável — o teste do espécime sem trava

> **Se dá pra cumprir a regra 100% e a garantia que ela promete ainda falhar, é ritual.**

O nome vem do espécime que provou a coisa: um backend com ports em `abc.ABC` em 10 de 10 adapters, vertical slices limpas, `README` afirmando seguir Clean Architecture estritamente — e bugs vivos passando por todos os buracos, porque o type-checker tinha sido removido e não havia import-linter. Forma perfeita, garantia zero.

A saída de uma posição que reprova aqui é sempre a mesma: **amarrar o check que faz cumprir implicar garantir, ou cortar a regra.** Não existe terceira via "documentar melhor".

Esta é a checagem mais destrutiva das três. Ela matou, entre outras: a própria régua antiga de admissão ao kernel ("2+ contextos usam"), que um espécime cumpria em 100% dos habitantes enquanto o kernel virava um contexto; a exigência de docstring em método de adapter, que fabricava prosa duplicada derivando em silêncio; e a façade de camada, cuja regra 92% do código já desobedecia sem que máquina nenhuma pudesse notar.

### 6.3 Autoridade não preenche

"A spec manda", "o pattern original define assim", "o autor recomenda" — tudo isso é insumo **definitional**. A justificativa é sempre cenário mais evidência.

O teste de sinceridade desta checagem é ela morder também os aliados. O mesmo cânone Python foi usado **a favor** da posição sobre forma de use-case e apareceu como **rival vencido** na posição sobre transações, na mesma sessão, sem cherry-picking. Uma fonte que só aparece quando concorda não está sendo consultada — está sendo citada.

## 7. Como propor mudança

1. **Identifique a posição e leia o gatilho dela.** Se o teu caso bate no gatilho, a posição já prevê a tua situação: ela não se aplica, e não há discussão a ter.
2. **Classifique a tua alegação** pela tabela do §3. Se é comportamento de ferramenta, **rode o experimento** contra as versões pinadas antes de escrever qualquer coisa — a régua não aceita leitura de doc no lugar de medição, e três de quatro hipóteses do autor morreram exatamente aí durante as adjudicações.
3. **Passe pelo portão do §6**, nos dois sentidos. Nomeie o que dói fazendo e o que dói não fazendo.
4. **Escreva o dissenso invertido:** se a tua proposta vence, a posição atual vira a vice, e você deve o steelman dela.
5. **Atualize o gatilho.** Uma posição nova sem gatilho de reabertura é dogma, e não entra.
