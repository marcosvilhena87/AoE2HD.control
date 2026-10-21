# HD Selected Object Identification v1.7

Leitura **experimental e somente leitura** dos offsets candidatos `Player+0x15C`, `Player+0x160` e `Object+0x38` (bit `0x00010000`), descobertos em `selection_compare_v1_6.json`. A v1.7 **não implementa get_selected_object() como API estável**, nem inferência de seleção múltipla.

## Atualização no PowerShell
```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git fetch origin main
git reset --hard origin/main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
```
`reset --hard` elimina alterações rastreadas locais. Verifique `git status` antes.

## Validação em quatro fases
Use sempre Object IDs reais da sessão atual. Os exemplos 2180 (TC) e 2190 (aldeão **ilustrativo, precisa ser confirmado**) não são garantidos após reinício.

Sem seleção:
```powershell
python -m aoe2hdcontrol selected-v1-7 --pid $gamePid --ids 2180 2190 --allow-candidates --output sel17_baseline.json
```
Selecione manualmente o TC e capture:
```powershell
python -m aoe2hdcontrol selected-v1-7 --pid $gamePid --ids 2180 2190 --allow-candidates --output sel17_tc.json
```
Selecione manualmente um aldeão conhecido e capture:
```powershell
python -m aoe2hdcontrol selected-v1-7 --pid $gamePid --ids 2180 2190 --allow-candidates --output sel17_villager.json
```
Desselecione e capture:
```powershell
python -m aoe2hdcontrol selected-v1-7 --pid $gamePid --ids 2180 2190 --allow-candidates --output sel17_clear.json
```

## Hipóteses e controles
- `player_candidate_pointers.0x15c/0x160`: na sessão v1.6 passaram de zero ao endereço do TC e voltaram a zero. Confirmar com aldeão e múltiplas unidades.
- `selection_bit_16_candidate`: bit ligado em Object+0x38 observado em TC na seleção e desligado na desseleção. Testar outras classes.
- `matches_player_...` associa um ponteiro ao endereço de objeto **somente no conjunto de IDs solicitado**.
- Ao selecionar vários aldeões, observar se ambos ponteiros representam primeiro/último item ou outro arranjo; **não concluir a semântica apenas por dois ponteiros iguais**.
- Campos candidatos não promovidos a `AoE2HD.mapping`. Guardar JSON das fases e repetir em sessão independente.

Para evitar erros, a API retorna objetos ausentes em `errors` e CLI sinaliza código 2.
