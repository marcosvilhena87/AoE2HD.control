# v3.3.7 — validação por lote (sem comandos ao jogo)

A v3.3.7 consolida **10 ou mais relatórios independentes v3.3.6** contendo
`--measurement`. Não realiza leitura do processo, captura, clique, nem movimento
do cursor. Rejeita IDs da calibração e dos testes anteriores, objetos
duplicados, PID divergente, medições ausentes, erro não finito, projeções fora
da área cliente e registros com dispatch diferente de `not_dispatched`.

## Fluxo

1. Selecione uma nova unidade e identifique seu Object ID com `selected-v2-7`.
2. Capture uma evidência com `capture-anchor-v3-3-5`, usando JSON/BMP únicos.
3. Execute `observe-projection-v3-3-6 --measurement <json> --output <unico>.json`.
4. Repita com 10 unidades inéditas distintas, sem alterar a câmera.
5. Execute o comando abaixo; substitua os nomes do curinga com a relação de arquivos desejados.

```powershell
$arquivos = @(Get-ChildItem .\json\validacao_nova_*.json | ForEach-Object FullName)
if ($arquivos.Count -lt 10) { throw "São necessários pelo menos dez relatórios" }
python -m aoe2hdcontrol validate-projections-v3-3-7 `
  --reports $arquivos `
  --exclude-ids 2630 2629 2623 2576 2627 `
  --min-samples 10 --threshold-px 25 `
  --output json\lote_v3_3_7.json
Get-Content .\json\lote_v3_3_7.json -Raw
```

Métricas: média do erro euclidiano, RMSE, máximo, percentil 95 (nearest rank)
e fração dos pontos com erro <=25 px. A aprovação é **numérica e candidata**,
não é permissão para clicar. A identidade visual no BMP, a câmera estacionária
e o enquadramento ainda exigem inspeção humana. Não use as unidades 2630,
2629, 2623, 2576 e 2627 como inéditas.
