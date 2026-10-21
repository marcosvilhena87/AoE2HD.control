# Selected Objects API v2.2 — Experimental Selection Enumeration

Baseada na observação v2.1: objetos selecionados apareceram consecutivamente em `Player+0x160`, `+0x164`, `+0x168`. Trata-se de hipótese de layout; não é fonte canônica validada.

O leitor varre até 16 posições por padrão (máximo 32) a partir de `Player+0x160`, verifica ID candidato em `Object+0x08`, confronta com `get_object_by_id` (tabela existente), e valida bit `Object+0x38 & 0x10000`. Lê mesmo após entradas zero e registra discrepâncias em `anomalies`. Sem escrita, sem varredura global e sem percorrer ponteiros não confirmados por tabela.

## PowerShell
```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git pull --ff-only origin main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
```
Ajuste a seleção manualmente e capture em estados separados:
```powershell
# nenhuma unidade selecionada
python -m aoe2hdcontrol selected-v2-2 --pid $gamePid --max-entries 16 --allow-candidates --output selected_v2_2_clear.json
# selecione tres ou mais unidades moveis
python -m aoe2hdcontrol selected-v2-2 --pid $gamePid --max-entries 16 --allow-candidates --output selected_v2_2_units.json
# selecione duas ou mais construcoes (separadas das unidades moveis)
python -m aoe2hdcontrol selected-v2-2 --pid $gamePid --max-entries 16 --allow-candidates --output selected_v2_2_buildings.json
```

## Python
```python
from aoe2hdcontrol.selected_objects_v2_2 import enumerate_selected,get_selected_objects,get_selected_count
report=enumerate_selected(api,max_entries=16)
objects=get_selected_objects(api,max_entries=16)  # tupla de dicionarios resumidos
count=get_selected_count(api,max_entries=16)  # quantidade verificada na janela, não total global
```

Os resultados representam o subconjunto de objetos da janela lida que passou pela checagem de tabela e flag. O campo `completeness` é sempre `unknown`, porque ainda não sabemos o tamanho, contador ou terminador real da lista. `first_zero_index`, `nonzero_after_first_zero` e `truncated_at_limit` são diagnósticos, nunca prova de completude. Não foram modificados offsets do repositório `AoE2HD.mapping`.
