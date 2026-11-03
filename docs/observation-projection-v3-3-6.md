# v3.3.6 — projeção operacional somente observação

Lê o Object ID e a posição candidata (Object+0x3C/0x40), aplica o
**relatório aprovado na triagem** v3.3.2 com ajuste v3.3 e verifica
limites informados da área cliente. Sem cliques, escrita de memória ou
seleção. O modelo é específico da sessão/enquadramento; não recupera
automaticamente mudanças de câmera.

## Executar com a calibração que apresentou RMSE=8,77 px

```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
git fetch origin
git switch feat/v3-3-6-observation-projection
git pull --ff-only
python -m unittest discover -s tests -v
$gamePid=(Get-Process 'AoK HD').Id
python -m aoe2hdcontrol observe-projection-v3-3-6 `
  --pid $gamePid --id 2576 --allow-candidates `
  --fit json/calibracao_final_v3_3_5.json `
  --client-width 1536 --client-height 864 `
  --output json/previsao_2576_v3_3_6.json

Get-Content .\json\previsao_2576_v3_3_6.json -Raw
```

Para **nova medição independente**, use `capture-anchor-v3-3-5`
em imagem e JSON novos (não reutilize medições participantes do ajuste),
e acrescente `--measurement json/nova_medicao.json`. A comparação
exige PID/ID iguais, posição de mundo estável e evidência candidata.
`measurement_comparison` é comparação numérica do cursor, não
verificação por visão computacional. A prova de câmera estacionária
e da correspondência unidade/cursor permanece pendente.
