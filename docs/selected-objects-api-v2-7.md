# Selected Objects API v2.7 — consistência de snapshots

Somente leitura. Requer `--allow-candidates`. Consome os mesmos candidatos
`LocalPlayer+0x160` (vetor) e `LocalPlayer+0x254` (contagem) da v2.6,
sem promover seu status. Capacidade observada: até 60 unidades móveis.

## Mudança principal
Compara **três vetores completos de ponteiros** e **cinco leituras do
contador**: antes da validação de objetos, durante o processo e depois.
Isso detecta trocas de seleção com contagem constante quando observáveis
nas capturas. Não é atômico, não detecta toda mudança ABA, não prova
completude e não substitui validação em novas sessões.

Estados: `stable_with_candidate_count`, `selection_changed`,
`counter_changed`, `invalid_count`, `invalid_entries`.
Somente o estado estável disponibiliza `selected_objects` e
`selected_count_verified`. Os vetores brutos e anomalias permanecem no JSON.

## Execução
```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
python -m aoe2hdcontrol selected-v2-7 --pid $gamePid --allow-candidates --output selected_v2_7.json
Get-Content .\selected_v2_7.json -Raw
```

## Referências
- `AoE2HD.mapping`: catálogo canônico e evidência v2.6 de 21/10/2026.
- `AoE2HD.aoe2control`: referência de comportamento DE, **sem** compatibilidade binária presumida.
- `AoE2HD.control`: implementação v2.6, preservada; testes v2.7 com simuladores.
- Capturas do operador desta conversa: 0, 1, 10, 60 móveis e 1, 12 construções,
  todas sem anomalias; não são reprodução independente nem validação em runtime v2.7.
