# Selected Objects API v2.7 — verificação repetida de identidade

Consulta cruzada: `AoE2HD.control` v2.6, `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md` e `AoE2HD.mapping/docs/evidencia_selecao_v2_6_2026-10-21.md`.

## Mudança
A v2.6 verifica três leituras do contador candidato `LocalPlayer+0x254`, mas não detecta necessariamente substituições de objetos que preservem a contagem. A v2.7 executa **duas observações completas da v2.6** e compara a sequência ordenada de `(object_id, address)`.

Somente duas observações individualmente consistentes e idênticas retornam `selected_objects` e `selected_count_verified`. Caso contrário, os resultados consolidados são descartados e ambas as observações ficam disponíveis para auditoria.

Estados: `repeated_observations_agree`, `selection_changed_same_or_different_count`, `unstable_or_invalid_observation`.

## Uso
```powershell
python -m aoe2hdcontrol selected-v2-7 --pid $gamePid --allow-candidates --output selected_v2_7.json
python -m unittest discover -s tests -v
```

## Limites
- **Não é snapshot atômico**: alterações do tipo ABA entre leituras ainda podem passar despercebidas.
- `completeness=unknown`; duas leituras concordantes não demonstram cobertura global.
- A ordem integra a comparação, logo reordenação sem troca de membros também é sinalizada.
- Os offsets permanecem candidatos, sem alterações no catálogo canônico.
- Testes unitários não substituem capturas reais na build `AoK HD.exe 5.8.INT` (x86); capturar após reinício e registrar hash SHA-256 do executável.

## Capturas reais recebidas em 21/10/2026

Seis JSON analisados: `clear=0`, `60=60`, `buildings=15`, `group_A=60`, `group_B=60` e `selected_v2_7.json=60`. Todos com `repeated_observations_agree`, 12 observações internas concordantes e zero anomalias registradas. Os grupos A e B possuem 46 IDs comuns e 14 exclusivos em cada grupo: identidades diferentes com contagens iguais, **entre execuções separadas**.

**Não confundir**: a mudança de grupo entre arquivos prova distinção por identidade na análise offline, mas não comprova detecção de mudanças concorrentes **dentro** de uma execução. Ainda faltam experimento concorrente, reinício independente, hash da build e comprovação de cobertura global. Evidência detalhada registrada em [AoE2HD.mapping](https://github.com/marcosvilhena87/AoE2HD.mapping/blob/main/docs/evidencia_selecao_v2_7_2026-10-21.md). Arquivos JSON originais não estão versionados.
