# HD Object API Validation v1.6 — Selection Memory Discovery

Objetivo: localizar **candidatos de estado de seleção** por captura diferencial de regiões pequenas e já identificadas. A API só lê memória e não controla o jogo.

## Executar no PowerShell

```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git fetch origin main
git reset --hard origin/main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
```

Confirme que não há alterações locais importantes antes de resetar.

Para todas as fases, use exatamente o mesmo `--session`, `--ids` e arquivo `--output`. Se o jogo reiniciar, use outro arquivo e outra sessão.

**Fase 1 — sem seleção:**
```powershell
python -m aoe2hdcontrol selection-v1-6 --pid $gamePid --session sel01 --phase baseline --ids 2180 2181 2182 2183 --allow-candidates --output selection_v1_6.json
```

**Fase 2 — selecione manualmente o Centro da Cidade:**
```powershell
python -m aoe2hdcontrol selection-v1-6 --pid $gamePid --session sel01 --phase tc_selected --ids 2180 2181 2182 2183 --allow-candidates --output selection_v1_6.json
```

**Fase 3 — desselecione manualmente:**
```powershell
python -m aoe2hdcontrol selection-v1-6 --pid $gamePid --session sel01 --phase deselected --ids 2180 2181 2182 2183 --allow-candidates --output selection_v1_6.json
```

**Fase 4 (opcional) — selecione um aldeão:** repita com `--phase villager_selected`, mantendo os mesmos IDs, e registre o ID do aldeão de forma separada, pois esta fase não infere automaticamente sua identidade.

**Comparar:**
```powershell
python -m aoe2hdcontrol compare-selection-v1-6 --input selection_v1_6.json --output selection_compare_v1_6.json
```

## O que é amostrado

- Primeiros 512 bytes da estrutura do jogador local, se legíveis.
- Primeiros 256 bytes de até 16 objetos, por Object ID da partida atual.
- Usar `--object-bytes` e `--player-bytes` para reduzir/alterar janelas (máximo 1024 cada).
- Alterações em palavras de 4 bytes, identificadas por região e deslocamento relativo.
- `reversible_candidates`: campo que muda na seleção e retorna ao valor inicial na desseleção (ordem baseline -> tc_selected -> deselected). Isso é correlação temporal **não validação**.

## Limitações

A varredura **não inclui o mundo todo**, estruturas de interface não catalogadas, nem apontadores aninhados. Não detectar um candidato aqui não demonstra ausência de um estado de seleção. A captura contém hex dump de pequenas regiões de memória do jogo; não a compartilhe se outros dados sensíveis estiverem carregados no processo. Se capturas apresentarem erros ou objetos ausentes, resultados são incompletos. Repetir em nova partida com seleção do aldeão como controle; só atualizar `AoE2HD.mapping` após validação independente.

A v1.6 implementa a infraestrutura da descoberta e não promete identificar o offset sem novos experimentos.
