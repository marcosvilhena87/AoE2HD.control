# Selected Objects API v2.3 — Capacity & Counter Discovery

A v2.2 identificou automaticamente 4 unidades móveis e 2 construções, usando slots em `Player+0x160`. A capacidade real continua desconhecida.

A v2.3 combina a enumeração v2.2 (até **32** entradas) com leitura independente de **64 bytes de Player+0x120 a +0x15F**. O comparador mostra campos que variaram e quais coincidiram numericamente com a contagem **verificada na janela**; essa igualdade não comprova um contador global.

## PowerShell

```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git pull --ff-only origin main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
$session = 'capacity01'
$file = 'selected_capacity_v2_3.json'
```

Após mudar manualmente a seleção no jogo, execute as fases adequadas usando sempre o mesmo PID, arquivo e sessão:

```powershell
python -m aoe2hdcontrol selected-v2-3 --pid $gamePid --phase clear --session $session --max-entries 32 --allow-candidates --output $file
python -m aoe2hdcontrol selected-v2-3 --pid $gamePid --phase four --session $session --max-entries 32 --allow-candidates --output $file
python -m aoe2hdcontrol selected-v2-3 --pid $gamePid --phase eight --session $session --max-entries 32 --allow-candidates --output $file
python -m aoe2hdcontrol selected-v2-3 --pid $gamePid --phase twelve --session $session --max-entries 32 --allow-candidates --output $file
python -m aoe2hdcontrol selected-v2-3 --pid $gamePid --phase sixteen --session $session --max-entries 32 --allow-candidates --output $file
python -m aoe2hdcontrol selected-v2-3 --pid $gamePid --phase over_sixteen --session $session --max-entries 32 --allow-candidates --output $file
python -m aoe2hdcontrol selected-v2-3 --pid $gamePid --phase clear_after --session $session --max-entries 32 --allow-candidates --output $file
python -m aoe2hdcontrol compare-selected-v2-3 --input $file --output selected_capacity_compare_v2_3.json
```

**Execute somente as fases que conseguir reproduzir de fato.** Não rotule como `eight` se havia menos que oito unidades; pule a fase ou reinicie com uma sessão nova. Se o jogo não permitir mais que certo número, documente isso separadamente. Não misture unidades móveis e construções na mesma seleção. Para comparar construções, use outra sessão e seleções homogêneas, mantendo as fases realmente observadas.

## Restrições

- Não considere `verified_count` capacidade total, nem `first_zero_index` terminador comprovado.
- `nearby_changing_words` são observações; `equal_verified_count_phases` apenas correlação.
- Se o primeiro zero não surgir nas 32 entradas, a leitura está limitada; não aumentar cegamente.
- Offset `+0x15C` faz parte da investigação de contadores, mas já há evidência de referência especial, não um contador validado.
- Nenhuma descoberta é promovida automaticamente em `AoE2HD.mapping`.
