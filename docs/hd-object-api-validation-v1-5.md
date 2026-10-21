# HD Object API Validation v1.5 — Behavioral Relationship Discovery

## Escopo
Captura **somente leitura** de objetos Genie 109, 618, 619 e 620 da faixa explícita (até 512 IDs). O operador realiza manualmente eventos no jogo e anota a fase. A ferramenta não lê seleção da interface, não cria/destroi objetos e não controla o jogo.

## Atualização (PowerShell)
```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git fetch origin main
git reset --hard origin/main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
```
Só use reset --hard sem alterações rastreadas que queira preservar. Reobtenha o PID se reiniciar o jogo.

## Experimento A — selecionar/desselecionar o Centro da Cidade
Sem modificar a partida, execute as etapas separadamente, após fazer a ação indicada na interface:
```powershell
python -m aoe2hdcontrol objects-v1-5 --pid $gamePid --start-id 2100 --end-id 2300 --session sessao01 --phase baseline --allow-candidates --output tc_behavior_v1_5.json
# Selecione manualmente seu Centro da Cidade
python -m aoe2hdcontrol objects-v1-5 --pid $gamePid --start-id 2100 --end-id 2300 --session sessao01 --phase selected --allow-candidates --output tc_behavior_v1_5.json
# Desselecione manualmente
python -m aoe2hdcontrol objects-v1-5 --pid $gamePid --start-id 2100 --end-id 2300 --session sessao01 --phase deselected --allow-candidates --output tc_behavior_v1_5.json
python -m aoe2hdcontrol compare-v1-5 --input tc_behavior_v1_5.json --output tc_behavior_compare_v1_5.json
```

## Experimento B — construir ou destruir TC
Em partida **experimental separada**, com backup/save apropriado, anote `baseline` antes e `built` ou `destroyed` depois. Use `--session sessao02` e **outro arquivo** JSON. Se novos IDs forem criados acima da faixa original, amplie o intervalo mantendo **exatamente a mesma faixa em todas as fases**, no máximo 512 IDs. Sem cobertura do intervalo, ausência de objetos não comprova destruição.

## Interpretação
- `appeared_ids` e `disappeared_ids` referem-se apenas a objetos de classe 3 e tipos 109/618/619/620 dentro da faixa; mudança de tipo pode parecer desaparecimento.
- `changed` detecta mudanças de endereço, classe, tipo, dono e posição candidata.
- A captura não lê bits de seleção nem detecta seleções automaticamente. Seleção manual e campo `phase` são metadados do operador.
- Capturas com erro são marcadas como incompletas, e código de saída 2; não inferir ausência.
- Comparação rejeita session IDs divergentes e intervalos diferentes; IDs absolutos não devem ser comparados entre partidas.
- Se a seleção não alterar os campos observados, isso **não refuta** relações funcionais não instrumentadas.
- Nenhum status no AoE2HD.mapping deve ser promovido sem validação independente.

Arquivos brutos de evidência gerados localmente não são enviados automaticamente ao GitHub. A v1.5 é primeiro passo comportamental; ainda não implementa detecção real do objeto selecionado.
