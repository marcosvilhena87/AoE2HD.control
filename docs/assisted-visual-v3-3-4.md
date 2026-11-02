# v3.3.4 — validação visual assistida

Modo somente leitura e offline. Acrescenta confirmação **manual** de Object ID e
ponto visual `unit_base_center` aos JSON produzidos pela v3.3.2. A janela
é registrada como geometria fornecida pelo operador. A comparação de
recapturas testa identidade do PID/ID, deslocamento no mundo, posição
do cursor e igualdade de geometria; a câmera permanece `unknown`.

## Preparar geometria da janela (PowerShell)

No jogo na mesma posição, execute na sessão PowerShell:

```powershell
# Exemplo: substitua pelos valores REAIS da janela e área cliente.
# O preenchimento manual não detecta mudanças que ocorreram antes.
$janela = @{
 left=0; top=0; width=1535; height=863
 client_origin_x=0; client_origin_y=0; client_width=1535; client_height=863
}
$janela | ConvertTo-Json | Set-Content json/janela_v3_3_4.json -Encoding UTF8
```

## Confirmar duas capturas da mesma unidade

Antes de cada comando, confira visualmente o Object ID e o cursor sobre
o **centro da base da unidade**; `--operator-confirmed` é uma declaração
manual explícita, não uma verificação por visão computacional.

```powershell
python -m aoe2hdcontrol confirm-anchor-v3-3-4 `
  --anchor json/ancora_2630.json --id 2630 --operator-confirmed `
  --window-json json/janela_v3_3_4.json `
  --output json/2630_confirmado_A.json

python -m aoe2hdcontrol confirm-anchor-v3-3-4 `
  --anchor json/ancora_2630_recheck.json --id 2630 --operator-confirmed `
  --window-json json/janela_v3_3_4.json `
  --output json/2630_confirmado_A2.json

python -m aoe2hdcontrol compare-assisted-v3-3-4 `
  --first json/2630_confirmado_A.json `
  --last json/2630_confirmado_A2.json `
  --output json/2630_comparacao_v3_3_4.json
```

**Importante:** não marque como confirmado um arquivo antigo se você
não puder atestar que o cursor estava exatamente na base visual na
captura original. Nesse caso, faça novas capturas com v3.3.2, com
posicionamento deliberado e câmera fixa. A geometria fornecida não é
captura automática da janela, nem validação de câmera. O resultado
`candidate_repeatable` é apenas triagem, não habilita cliques.
