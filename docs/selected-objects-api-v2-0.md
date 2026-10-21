# Selected Objects API v2.0

Implementação **experimental, somente leitura**, baseada nos experimentos com seleção individual (v1.7), dois aldeões (v1.8) e três aldeões (v1.9).

## API Python
```python
from aoe2hdcontrol.selected_objects_v2_0 import (
    is_object_selected, get_selected_objects, get_selected_count, diagnose
)
# Todas exigem HDObjectAPI(..., allow_candidates=True)
is_object_selected(api, 2191)           # bool ou None (objeto ausente)
get_selected_objects(api, [2191,2190,2192]) # tupla de HDObject selecionados dentre os IDs
get_selected_count(api, [2191,2190,2192])   # contagem só dos IDs informados
diagnose(api, [2191,2190,2192])          # diagnóstico de flags e referências
```

Não há `get_selected_objects()` global sem IDs. Uma lista completa requer descoberta de estrutura de enumeração.

## CLI: comparação com seleção do jogo
```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git pull --ff-only origin main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
$ids = @(2191,2190,2192)
```
Os IDs devem ser reconfirmados na partida atual. Salve uma captura após cada ação manual no jogo:

```powershell
# nenhum selecionado
python -m aoe2hdcontrol selected-v2-0 --pid $gamePid --ids $ids --allow-candidates --output selected_v2_0_clear.json
# selecione os três
python -m aoe2hdcontrol selected-v2-0 --pid $gamePid --ids $ids --allow-candidates --output selected_v2_0_trio.json
# desselecione os três
python -m aoe2hdcontrol selected-v2-0 --pid $gamePid --ids $ids --allow-candidates --output selected_v2_0_after.json
```

A ferramenta inspeciona no máximo 64 IDs e até 512 bytes a partir de Player local, em passos alinhados de 4 bytes, buscando valores iguais a endereços dos objetos fornecidos. Ela **não percorre arbitrariamente ponteiros** nem varre regiões globais. `player_pointer_matches` apenas indica coincidências de valores; não prova lista ou ordem. `flagged_count_among_probed` é contagem parcial; falhas de leitura aparecem em `errors`.

**Importante:** offsets `Object+0x38`, `Player+0x15C`, `Player+0x160` continuam hipóteses experimentais e não foram promovidos em AoE2HD.mapping. Repetição em partidas independentes é requisito para validação canônica.
