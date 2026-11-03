# v3.6 — referência por um segundo aldeão (experimental)

Objetivo: medir aproximação do aldeão A a um aldeão B estacionário, preservando a v3.5 e **sem alegar comando nativo por Object ID**.

## Procedimento
1. Partida local/offline `AoK HD.exe 5.8.INT`; identifique dois aldeões (Genie Type ID 83), **A e B**, com IDs individuais da mesma sessão. Para obter B, selecione-o sozinho e rode `selected-v2-7`; depois selecione A sozinho e repita.
2. Deixe B parado, relativamente longe de A. Selecione somente A.
3. Identifique visualmente um **ponto de terreno livre adjacente a B** em coordenadas CLIENTE; não clique sobre a unidade B, para evitar interações.
4. Execute `experiment` com `armed=True`, `offline_confirmed=True`, IDs distintos e coordenadas cliente escolhidas. Use a mesma invocação via script em arquivo adotada na v3.5 (não `input()` dentro de `python -`).
5. Inspecione `comparison.initial_distance_candidate`, `comparison.final_distance_candidate`, `comparison.reference_displacement_candidate` e `movement.metrics.samples`.

```python
from aoe2hdcontrol.villager_reference_v3_6 import experiment
# with WindowsProcessReader(pid) as reader:
#     api = HDObjectAPI(reader, mapping_dir(), allow_candidates=True)
#     report = experiment(api, pid=pid, mover_id=ID_A, reference_id=ID_B,
#                         client_x=X_LIVRE, client_y=Y_LIVRE,
#                         armed=True, offline_confirmed=True)
```

O monitor usa intervalos de 200 ms por até 5 segundos e envia no máximo um clique direito normal do Windows. Não controla B. Se B se deslocar acima de 0,10 unidade candidata, o resultado indica `reference_moved`; se A parar a até 1,0 unidade candidata de B, o resultado indica `candidate_proximity_observed`. Esses limites são arbitrários para investigação, não raios de colisão estabelecidos. O resultado nunca afirma chegada verificada. Falha de leitura/identidade gera `observation_blocked`. Não é comprovada a relação geométrica entre o pixel clicado e a posição do mundo, tampouco aceitação pelo motor do jogo.

**Fontes consultadas:** `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md` (CMD-001 bloqueado, OBJ-004 candidato); `AoE2HD.mapping/docs/mapa.md` (IDs e offsets experimentais); `AoE2HD.control` v3.4/v3.5. Nenhum offset descoberto ou promovido. Executar `python -m unittest discover -s tests -p "test_villager_reference_v3_6.py" -v` e coletar dois experimentos após reiniciar o jogo antes de ampliar as conclusões.
