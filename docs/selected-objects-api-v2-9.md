# v2.9 — gate de despacho e auditoria de transições externas

A v2.9 **não implementa seleção programática efetiva**. A documentação
de compatibilidade HD marca despacho de comandos como `bloqueado`; não existe
mecanismo demonstrado para enviar uma seleção por Object ID ao executável.
`dispatch_selection` falha de maneira explícita (`DispatchUnavailable`)
inclusive quando recebe um backend fornecido pelo chamador; nunca escreve
memória e nunca produz evento de teclado/mouse.

Implementado: `evaluate_external_transition` compara dois JSONs reais v2.7
capturados *antes* e *depois* de uma seleção manual. Classifica:
- `external_transition_observed`: estado estável passou de outro grupo ao alvo;
- `already_selected_before`: alvo já estava presente antes;
- `target_not_observed`: estado final não corresponde;
- `inconclusive_snapshot`: snapshot ausente/inconsistente.

A comparação não prova qual ação causou a mudança; relatórios usam
`execution=not_dispatched`, `causality=unproven` e `completeness=unknown`.

## Experimento no PowerShell

```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id

# Capture antes, com outro objeto ou sem seleção:
python -m aoe2hdcontrol selected-v2-7 --pid $gamePid --allow-candidates --output v29_before.json

# Selecione MANUALMENTE uma unidade e identifique seu ID:
python -m aoe2hdcontrol selected-v2-7 --pid $gamePid --allow-candidates --output v29_after.json
$r = Get-Content .\v29_after.json -Raw | ConvertFrom-Json
$r.selected_objects | Select-Object object_id, class_id, genie_type_id

# Substitua <ID_REAL> pelo ID observado; não digite os sinais <>:
python -m aoe2hdcontrol compare-selected-v2-9 --before v29_before.json --after v29_after.json --ids 2626 --output v29_transition.json
Get-Content .\v29_transition.json -Raw
```

O exemplo `2626` não é ID persistente: use o ID da sessão atual.
Código de saída 0 indica somente transição externa observada; 2 indica
outros estados, 1 indica erro.

## Referências cruzadas (02/11/2026)
- `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md`: CMD-001
  bloqueado; API da DE não é ABI do HD.
- `AoE2HD.mapping/docs/evidencia_selecao_v2_6_2026-10-21.md`:
  offsets candidatos, sem capacidade física ou hash de build confirmado.
- `AoE2HD.control`: v2.7 snapshots e v2.8 intenções, mantidos.

## Próxima dependência
Investigar e validar **fora deste módulo** um mecanismo HD de envio de seleção
com teste positivo, negativo, rollback e autorização explícita, limitado a
partidas locais. Só então implementar despacho verdadeiro em revisão posterior.
