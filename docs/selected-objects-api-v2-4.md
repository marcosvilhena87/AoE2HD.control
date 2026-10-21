# Selected Objects API v2.4 — Consistency & Completeness Diagnostics

A v2.3 identificou 0/4/8/12/16/20 objetos em capturas controladas, todos com primeira posição zero igual à quantidade verificada, mas ainda não há prova do tamanho máximo nem do terminador real.

A v2.4 executa **duas enumerações completas consecutivas** via v2.2, verificando endereços do jogador, valores de cada slot, status, ID candidato, word de seleção e objetos verificados. Cada coleta é somente leitura e **não atômica**.

## Estados
- `stable_within_window`: leituras iguais, sem anomalia, com pelo menos um zero dentro do limite. **Não significa completude global.**
- `bounded_unterminated`: leituras iguais, porém janela termina sem zero observado.
- `inconsistent`: leituras iguais mas com anomalias ou dados após o primeiro zero.
- `unstable`: diferença entre as leituras; objetos não são promovidos a resultado consolidado.

Em todos os casos `completeness` permanece `unknown`. Com `unstable`, `selected_count_verified` é `null` e `selected_objects` é lista vazia; as duas observações permanecem no JSON para auditoria.

## PowerShell
```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git pull --ff-only origin main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id

# Com a seleção vazia:
python -m aoe2hdcontrol selected-v2-4 --pid $gamePid --max-entries 32 --allow-candidates --output selected_v2_4_clear.json

# Com 20 unidades móveis selecionadas:
python -m aoe2hdcontrol selected-v2-4 --pid $gamePid --max-entries 32 --allow-candidates --output selected_v2_4_twenty.json

# Com duas ou mais construções selecionadas:
python -m aoe2hdcontrol selected-v2-4 --pid $gamePid --max-entries 32 --allow-candidates --output selected_v2_4_buildings.json
```

Validação ideal: repetir seleção de 20 unidades numa partida independente e, se possível, testar mais de 20 sem ultrapassar o limite de 32 entradas configurado. **Não misture grupos de unidades móveis e de construções.**

Saída 0 indica `stable_within_window`; saída 2 é diagnóstico não plenamente consistente/terminado; saída 1 indica erro de execução.

Nenhuma descoberta é promovida automaticamente ao repositório canônico `AoE2HD.mapping`.
