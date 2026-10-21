# Selected Objects API v2.5 — 60 mobile units / 64-slot bounded read

O operador observou o limite de **60 unidades móveis** simultaneamente selecionadas no AoE II HD. Esse é o limite de interface relatado, não a capacidade física comprovada da memória. A v2.5 investiga até **64** ponteiros de 4 bytes a partir de `Player+0x160` (entrada 60 em `+0x250`), com duas leituras consecutivas, confirmação via Object ID, tabela de objetos e bit `Object+0x38 & 0x10000`.

## Atualizar
```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git pull --ff-only origin main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
```

Altere a seleção manualmente antes de cada linha. Selecione **somente unidades móveis** nos experimentos de 32, 40, 50 e 60, em caso de não haver essa quantidade, não rotule a captura com número maior.

```powershell
# 0 unidades:
python -m aoe2hdcontrol selected-v2-5 --pid $gamePid --max-entries 64 --allow-candidates --output selected_v2_5_clear.json
# 32 unidades móveis:
python -m aoe2hdcontrol selected-v2-5 --pid $gamePid --max-entries 64 --allow-candidates --output selected_v2_5_32.json
# 40 unidades móveis:
python -m aoe2hdcontrol selected-v2-5 --pid $gamePid --max-entries 64 --allow-candidates --output selected_v2_5_40.json
# 50 unidades móveis:
python -m aoe2hdcontrol selected-v2-5 --pid $gamePid --max-entries 64 --allow-candidates --output selected_v2_5_50.json
# 60 unidades móveis:
python -m aoe2hdcontrol selected-v2-5 --pid $gamePid --max-entries 64 --allow-candidates --output selected_v2_5_60.json
```

Também é útil capturar construções em um arquivo separado, sem misturar com unidades móveis.

## Uso Python
```python
from aoe2hdcontrol.selected_objects_v2_5 import inspect_selection, get_selected_objects, get_selected_count
report = inspect_selection(api, max_entries=64)  # api.allow_candidates=True
objects = get_selected_objects(api, max_entries=64)
count = get_selected_count(api, max_entries=64)
```

Resultados incluem `consistency` (`unstable`, `inconsistent`, `bounded_unterminated`, `stable_within_window`), `selected_count_verified`, `first_zero_index`, `window_exhausted`, `observations` e `completeness: unknown`. São duas leituras **não atômicas**; estabilidade numa janela não prova enumeração completa, terminador formal ou capacidade física. Em leituras instáveis ou anômalas, o resultado consolidado não é fornecido. Não promover automaticamente novos offsets ao `AoE2HD.mapping`.

A v2.5 é módulo novo: não altera o limite de 32 entradas das versões anteriores.
