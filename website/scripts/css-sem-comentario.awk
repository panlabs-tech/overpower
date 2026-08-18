# Remove os comentários de um CSS preservando arquivo, número de linha e o
# código que sobra. Saída no formato `arquivo:linha:código`, que é exatamente o
# que os portões 1, 2 e 3 esperam de um `grep -rn`.
#
# Por que isto existe: os portões varrem DECLARAÇÃO, não prosa. Um comentário que
# explica *"a âncora usa até 448px"* ou *"morre por alguém escrever
# `outline: none`"* é a documentação do valor, não o valor — e reprovar por causa
# dela ensinaria a escrever comentário pobre, que é o oposto do que este
# repositório quer. Sem isto, a saída correta seria apagar a explicação.
#
# Estado atravessa linha, então comentário de bloco multilinha some inteiro.

BEGIN { dentro = 0 }

{
  linha = $0
  fora = ""

  while (1) {
    if (dentro) {
      i = index(linha, "*/")
      if (i == 0) { linha = ""; break }
      linha = substr(linha, i + 2)
      dentro = 0
    } else {
      i = index(linha, "/*")
      if (i == 0) { fora = fora linha; linha = ""; break }
      fora = fora substr(linha, 1, i - 1)
      linha = substr(linha, i + 2)
      dentro = 1
    }
  }

  print FILENAME ":" FNR ":" fora
}
