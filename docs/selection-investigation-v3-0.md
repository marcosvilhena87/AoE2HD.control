# v3.0 — Investigação de despacho de seleção (observacional)

**Ainda não há despacho programático de seleção por Object ID.**
A v3.0 investiga seleção feita manualmente pelo operador com duas capturas
v2.7 no **mesmo handle de processo**, separadas por confirmação explícita no
PowerShell. A ferramenta não emite eventos ou grava memória.

## Experimento

```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
git fetch origin
git switch feat/v3-0-selection-dispatch-investigation
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id

# Identifique previamente o ID-alvo da sessão (exemplo: 2613).
# Antes de iniciar, mantenha OUTRA unidade selecionada.
python -m aoe2hdcontrol investigate-selection-v3-0 --pid $gamePid --ids 2613 --allow-candidates --output selection_v3_0.json

# Quando solicitado, selecione MANUALMENTE a unidade-alvo no jogo e pressione Enter.
$r = Get-Content .\selection_v3_0.json -Raw | ConvertFrom-Json
$r | Select-Object status, pid, context_same_player, dispatch, execution, causality
```

IDs variam entre sessões. Um resultado `external_transition_observed`
confirma apenas que a seleção mudou entre as duas observações, **não** que o
código enviou ordem. O comando retorna 0 nesse caso; 2 para demais estados.

O experimento rejeita a comparação causal quando o endereço/slot do jogador
diferir entre snapshots (`player_context_changed`). Isso não constitui uma
proteção plena contra PID reutilizado, reinício do jogo ou reuso de endereço.
As leituras não são atômicas. `completeness=unknown`.

## Revisão cruzada

- `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md`: comandos
  da DE não demonstram mecanismo de despacho HD; CMD-001 permanece bloqueado.
- `AoE2HD.mapping/docs/evidencia_selecao_v2_6_2026-10-21.md`: vetor,
  contador e flag com estado experimental; nenhum offset promovido.
- `AoE2HD.control` v2.7/v2.8/v2.9: snapshots, intenções e auditoria
  de transição, respectivamente.

## Próximos passos

Verificar hash/build do executável, repetir com PID renovado, investigar
mecanismo de comando sob evidência controlada e somente habilitar envio após
documentar aceitação, execução e testes negativos. Nenhum dispatch real
é implementado nesta revisão.
