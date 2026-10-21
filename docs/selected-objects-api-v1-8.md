# Selected Objects API v1.8 — Multiple Selection Discovery

**Objetivo:** testar seleção múltipla em Age of Empires II HD, sem escrever no processo nem considerar os offsets validados.

## Pré-requisitos e atualização

No PowerShell, na pasta do projeto:
```powershell
git status --short
git fetch origin main
git reset --hard origin/main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
```
ATENÇÃO: `reset --hard` descarta alterações locais rastreadas. Faça backup caso existam.

É necessário conhecer os **Object IDs atuais** de dois aldeões distintos. O ID 2191 já foi identificado anteriormente, mas confirme sua validade na sessão atual. Para achar outro aldeão, selecione-o sozinho e consulte `Player+0x15C` e o `Object+0x08` conforme o roteiro v1.7. Não use valores arbitrários.

## Protocolo de cinco fases

Defina os IDs confirmados (substitua 2192 se necessário):
```powershell
$ids = @(2191,2192)
```
A ferramenta observa apenas esses IDs. Use mesmos IDs, mesma partida, `--session` e mesmo arquivo em todas as capturas.

1. Sem seleção:
```powershell
python -m aoe2hdcontrol selected-v1-8 --pid $gamePid --ids $ids --phase clear --session multi01 --allow-candidates --output selected_multi_v1_8.json
```
2. Selecione apenas o primeiro aldeão:
```powershell
python -m aoe2hdcontrol selected-v1-8 --pid $gamePid --ids $ids --phase single_first --session multi01 --allow-candidates --output selected_multi_v1_8.json
```
3. Selecione apenas o segundo aldeão:
```powershell
python -m aoe2hdcontrol selected-v1-8 --pid $gamePid --ids $ids --phase single_second --session multi01 --allow-candidates --output selected_multi_v1_8.json
```
4. Selecione ambos ao mesmo tempo (retângulo de seleção ou Ctrl, conforme interface):
```powershell
python -m aoe2hdcontrol selected-v1-8 --pid $gamePid --ids $ids --phase multi --session multi01 --allow-candidates --output selected_multi_v1_8.json
```
5. Desselecione ambos:
```powershell
python -m aoe2hdcontrol selected-v1-8 --pid $gamePid --ids $ids --phase clear_after --session multi01 --allow-candidates --output selected_multi_v1_8.json
```

Comparar:
```powershell
python -m aoe2hdcontrol compare-selected-v1-8 --input selected_multi_v1_8.json --output selected_multi_compare_v1_8.json
```

## Critérios de avaliação

- `flagged_ids_among_probed`: quais IDs consultados apresentam `Object+0x38 & 0x10000 != 0`.
- `candidate_pointers`: leituras brutas de `Player+0x15C` e `Player+0x160`.
- `pointer_matches`: identifica somente correspondências dos dois ponteiros aos IDs fornecidos.
- `errors`: leituras inválidas e IDs ausentes. Não inferir ausência de seleção quando houver erros.
- Ausência de um ID em `flagged_ids_among_probed` não demonstra que o objeto não está selecionado em todos os estados do jogo.
- Dois ponteiros não implicam lista completa. Não foi implementada enumeração global da seleção.

**Estado:** offsets `Object+0x38`, `Player+0x15C` e `Player+0x160` seguem candidatos e não foram promovidos automaticamente no repositório `AoE2HD.mapping`. Os testes offline não validam memória do processo em execução.
