# Selected Objects API v2.1 — Bounded Selection Layout Discovery

A v2.0 encontrou ponteiros para três aldeões em `Player+0x15C`, `+0x160`, `+0x164` e `+0x168`. A v2.1 lê **todas as palavras uint32 de Player+0x150 até +0x1AC**, inclusive valores sem correspondência com IDs conhecidos. Não presume início/fim, contador ou capacidade da lista.

## PowerShell

```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git pull --ff-only origin main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
$ids = @(2191,2190,2192)
$session = 'layout01'
$file = 'selected_layout_v2_1.json'
```

**Reconfirme os IDs na partida atual.** Para investigar `four_plus`, acrescente um quarto Object ID confirmado antes da primeira captura. Use o mesmo array de IDs em todas as fases, mesmo quando menos unidades estiverem selecionadas.

Execute após ajustar a seleção manualmente:

```powershell
python -m aoe2hdcontrol selected-v2-1 --pid $gamePid --ids $ids --phase clear --session $session --allow-candidates --output $file
python -m aoe2hdcontrol selected-v2-1 --pid $gamePid --ids $ids --phase single --session $session --allow-candidates --output $file
python -m aoe2hdcontrol selected-v2-1 --pid $gamePid --ids $ids --phase pair --session $session --allow-candidates --output $file
python -m aoe2hdcontrol selected-v2-1 --pid $gamePid --ids $ids --phase trio --session $session --allow-candidates --output $file
# fase four_plus somente quando 4+ unidades realmente selecionadas, caso contrário omita
python -m aoe2hdcontrol selected-v2-1 --pid $gamePid --ids $ids --phase clear_after --session $session --allow-candidates --output $file
python -m aoe2hdcontrol compare-selected-v2-1 --input $file --output selected_layout_compare_v2_1.json
```

Se houver quarto aldeão confirmado, inclua `--phase four_plus` antes de `clear_after`.

## Saída

- `slots`: offset, `value` uint32, hexadecimal e Object ID conhecido, se corresponder.
- `changed_slots`: valores brutos em cada fase para offsets que mudaram.
- `selected_ids_among_probed`: apenas objetos consultados com bit `Object+0x38 & 0x10000`.
- Ausência de correspondência não significa ponteiro inválido. Não se lê o endereço contido nos slots.
- Erros de leitura devem ser investigados; **não** inferir seleção global ou contador ainda.
- Não combinar no mesmo teste seleções móveis e construções: segundo observação do operador, o jogo não admite grupo misto.
- Novos offsets seguem como **candidatos**, sem promoção automática no `AoE2HD.mapping`.
