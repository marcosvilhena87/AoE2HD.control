# Selected Objects API v1.9

Investigação somente leitura da seleção simultânea de três ou mais unidades, com IDs conhecidos na partida.

## Atualizar
```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git pull --ff-only origin main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
```

Confirme os Object IDs de **três aldeões reais** e distintos na mesma partida. Os valores abaixo são apenas exemplos; 2190 e 2191 foram identificados em experimento anterior, mas devem ser conferidos no processo atual. **2192 não foi confirmado**.

```powershell
$ids = @(2191,2190,2192)
```

Prepare uma nova sessão/arquivo para não misturar com v1.8:
```powershell
$session = 'trio01'
$file = 'selected_trio_v1_9.json'
```

Execute cada comando após alterar manualmente a seleção no jogo. Para `multi_abc` e `multi_cba`, **altere a ordem efetiva de seleção** (não apenas a ordem dos IDs passados na linha de comando). Quando o jogo não permitir controlar a ordem, registre isso como limitação.

```powershell
python -m aoe2hdcontrol selected-v1-9 --pid $gamePid --ids $ids --phase clear --session $session --allow-candidates --output $file
python -m aoe2hdcontrol selected-v1-9 --pid $gamePid --ids $ids --phase single_a --session $session --allow-candidates --output $file
python -m aoe2hdcontrol selected-v1-9 --pid $gamePid --ids $ids --phase single_b --session $session --allow-candidates --output $file
python -m aoe2hdcontrol selected-v1-9 --pid $gamePid --ids $ids --phase single_c --session $session --allow-candidates --output $file
python -m aoe2hdcontrol selected-v1-9 --pid $gamePid --ids $ids --phase multi_abc --session $session --allow-candidates --output $file
python -m aoe2hdcontrol selected-v1-9 --pid $gamePid --ids $ids --phase multi_cba --session $session --allow-candidates --output $file
python -m aoe2hdcontrol selected-v1-9 --pid $gamePid --ids $ids --phase clear_after --session $session --allow-candidates --output $file
python -m aoe2hdcontrol compare-selected-v1-9 --input $file --output selected_trio_compare_v1_9.json
```

O comando lê `Player+0x15C`, `Player+0x160` e o bit `Object+0x38 & 0x10000` apenas dos IDs monitorados. `flagged_count_among_probed` **não** equivale à contagem global de objetos selecionados. Dois ponteiros não demonstram início/fim de lista nem ordenação. As descobertas permanecem candidatas; não promover automaticamente ao catálogo canônico `AoE2HD.mapping`.
