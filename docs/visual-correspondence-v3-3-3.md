# v3.3.3 — auditoria de correspondência visual A–B–A

Auditoria **somente leitura** dos JSON v3.3.2. Compara a primeira e
última captura da mesma unidade, intercaladas por outra. Mede deltas do
mundo e do cursor (pixels), verifica mesmo PID, IDs, validade das
capturas e informa limites configuráveis. NÃO identifica a câmera nem
comprova que o cursor corresponde ao Object ID. Um desvio não deve ser
rotulado como movimento de câmera.

## Executar nas evidências já coletadas

```powershell
git fetch origin
git switch feat/v3-3-3-visual-correspondence-audit
python -m unittest discover -s tests -v
python -m aoe2hdcontrol audit-aba-v3-3-3 `
  --first json/ancora_2630.json `
  --middle json/ancora_2629.json `
  --last json/ancora_2630_recheck.json `
  --output json/auditoria_aba_v3_3_3.json
Get-Content .\json\auditoria_aba_v3_3_3.json -Raw
```

Esperado nos dados relatados: world delta 0, cursor delta X=-830,
Y=-119, distância de aproximadamente 838,49 px. Isso não comprova
movimento da câmera, nem qualidade de correspondência visual.
O campo `camera_movement` permanece `unknown`; observação
`candidate_anchor` continua sem verificação visual de identidade.

Próximo experimento: captura manual com confirmação visual independente
e evidência de enquadramento constante, antes de reavaliar o ajuste.
