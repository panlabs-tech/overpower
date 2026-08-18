# Remove os comentários de um JavaScript preservando arquivo, número de linha e
# o código que sobra. Saída no formato `arquivo:linha:código`, que é exatamente o
# que uma varredura espera de um `grep -rn`.
#
# Irmão de `css-sem-comentario.awk`, e existe pelo mesmo motivo: **a varredura
# cobra código, não prosa.** Este repositório escreve comentário longo de
# propósito, e o comentário cita o que a regra proíbe — `Accordion.js` explica
# que *"um `<div onClick>` seria pixel a pixel idêntico"*, e essa frase é a
# documentação da regra. Sem isto, a varredura reprovaria a explicação e a saída
# correta seria apagá-la.
#
# Cobre `/* … */` (estado atravessa linha) e `//` até o fim da linha. Ele NÃO é
# um parser: `//` dentro de string literal ou de regex some junto. Para o que
# estas varreduras cobram — nome de handler e de API de DOM — o falso negativo é
# aceitável e o falso positivo não seria.

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
      bloco = index(linha, "/*")
      solta = index(linha, "//")
      if (solta > 0 && (bloco == 0 || solta < bloco)) {
        fora = fora substr(linha, 1, solta - 1)
        linha = ""
        break
      }
      if (bloco == 0) { fora = fora linha; linha = ""; break }
      fora = fora substr(linha, 1, bloco - 1)
      linha = substr(linha, bloco + 2)
      dentro = 1
    }
  }

  print FILENAME ":" FNR ":" fora
}
