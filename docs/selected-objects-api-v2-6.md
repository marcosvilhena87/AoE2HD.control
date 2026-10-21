# Selected Objects API v2.6 — Candidate-counter guided enumeration

A captura v2.5 indica que `Player+0x254` acompanha a contagem de unidades móveis (0, 32, 40, 50, 60). É um **candidato** ainda não validado em partidas independentes ou grupos de construções. A implementação lê somente `count * 4` bytes a partir de `Player+0x160`, limitando `count` ao intervalo de 0 a 60, o máximo de seleção móvel relatado pelo operador.

## Como executar

```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git pull --ff-only origin main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id

# Sem unidades selecionadas:
python -m aoe2hdcontrol selected-v2-6 --pid $gamePid --allow-candidates --output selected_v2_6_clear.json

# Selecionar manualmente 60 unidades móveis:
python -m aoe2hdcontrol selected-v2-6 --pid $gamePid --allow-candidates --output selected_v2_6_60.json

# Selecionar manualmente construções, separadas das unidades móveis:
python -m aoe2hdcontrol selected-v2-6 --pid $gamePid --allow-candidates --output selected_v2_6_buildings.json
```

## API

```python
from aoe2hdcontrol.selected_objects_v2_6 import inspect_selection, get_selected_objects, get_selected_count
report = inspect_selection(api)
objects = get_selected_objects(api)  # tupla de resumos; vazia se não for válido
count = get_selected_count(api)      # int ou None quando inválido
```

O contador é lido antes da lista, após capturar ponteiros e após verificar objetos. A enumeração valida cada Object ID na tabela canônica existente e `Object+0x38 & 0x10000`.

Estados: `consistent_with_candidate_count`, `counter_changed`, `invalid_entries`, `invalid_count`. Em casos inválidos os objetos consolidados são descartados, e as observações individuais ficam no JSON. `completeness` sempre `unknown`.

**Advertências:** três leituras sequenciais de contagem não são atômicas e não detectam necessariamente mudanças de seleção que preservam o número de objetos. O limite 60 vem da seleção de unidades móveis, não é prova de capacidade de memória nem de limite de construções. O experimento não promove offsets em `AoE2HD.mapping`.
