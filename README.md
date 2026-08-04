# overpower

CLI que instala **AI Frameworks** curados — corpos nomeados de equipamento de agente vindos de uma origem única — num repositório ou na máquina.

```bash
uvx overpower@latest
```

> **A série `0.0.x` não é o produto.** Ela existe para reservar o nome no PyPI e provar o pipeline de publicação ponta a ponta, nos dois caminhos de instalação: PyPI público e índice corporativo. Não instala nada — imprime a versão que chegou, o interpretador que a rodou e o payload que atravessou. A primeira versão utilizável é a `v0.1.0`.

## Por que `@latest`

O `uvx` **congela a versão indefinidamente** no primeiro uso, sem TTL. Como a versão do overpower *é* a versão do catálogo que ele embute, `uvx overpower` sem sufixo entrega catálogo velho em silêncio. `@latest` é requisito de correção, não estilo de README.

## O alias `op` colide

`op` é o comando do [1Password CLI](https://developer.1password.com/docs/cli/). Se você usa os dois, o alias precisa ser outro.

## Estado

Em construção, cartografado em [Mapa: overpower v0.1.0 publicada no PyPI](https://github.com/panlabs-tech/overpower/issues/1). O vocabulário, as regras do modelo e os axiomas estão em [`docs/agents/domain.md`](docs/agents/domain.md).

## Licença

MIT.
