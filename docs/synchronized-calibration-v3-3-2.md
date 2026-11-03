# v3.3.2 — calibração com âncoras temporalmente próximas

Capta posição candidata da unidade (`Object+0x3C/0x40`) entre **duas**
leituras do cursor em coordenadas da área cliente do Windows. Registra
`observation_window_ms`, timestamp UTC, PID, Object ID e foco.

**Não é amostragem atômica:** cursor estacionário entre leituras não
comprova câmera imóvel, nem que o cursor estava sobre o centro da
unidade. Confirme visualmente, e não mova câmera/unidade durante a captura.

## PowerShell

```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
git fetch origin
git switch feat/v3-3-2-synchronized-anchors
python -m unittest discover -s tests -v
$gamePid=(Get-Process 'AoK HD').Id

# Para cada ID, deixe câmera fixa, posicione cursor sobre centro
# da unidade durante os 5 segundos, não mova até terminar.
python -m aoe2hdcontrol capture-anchor-v3-3-2 --pid $gamePid --id 2630 --allow-candidates --output json/ancora_2630.json
python -m aoe2hdcontrol capture-anchor-v3-3-2 --pid $gamePid --id 2629 --allow-candidates --output json/ancora_2629.json
python -m aoe2hdcontrol capture-anchor-v3-3-2 --pid $gamePid --id 2623 --allow-candidates --output json/ancora_2623.json
python -m aoe2hdcontrol capture-anchor-v3-3-2 --pid $gamePid --id 2576 --allow-candidates --output json/ancora_2576.json

python -m aoe2hdcontrol fit-anchors-v3-3-2 --anchors json/ancora_2630.json json/ancora_2629.json json/ancora_2623.json json/ancora_2576.json --holdout-id 2576 --output json/calibracao_v3_3_2.json
Get-Content .\json\calibracao_v3_3_2.json -Raw
```

Os IDs são específicos da sessão: confirme cada ID antes de executar. O
fitting só aceita âncoras `usable`, do mesmo PID, sem IDs duplicados,
com ao menos três âncoras para ajuste e uma independente. Um RMSE
independente acima de 25 pixels ou geometria quase paralela/singular
gera `rejected`.

**Observação:** `candidate_fit_passed_threshold` é uma triagem numérica,
NÃO equivale a projeção/câmera validada; o modelo não é habilitado para
cliques. Repetir sessões e medir estabilidade da câmera ainda é necessário.
