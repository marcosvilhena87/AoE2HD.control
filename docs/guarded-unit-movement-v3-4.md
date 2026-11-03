# Guarded unit movement v3.4 (experimental)

## Escopo e referências
Implementação para AoK HD.exe 5.8.INT (PE32/x86), **não** equivalente ao `UnitsMove` do DE.
Antes da implementação foram consultados:
- AoE2HD.aoe2control: `docs/hd-compatibility-matrix-v3.md`, CMD-001 bloqueado e OBJ-004 pendente.
- AoE2HD.mapping: `README.md`; posições `Object+0x3C/+0x40` continuam candidatas.
- AoE2HD.control: `object_api.py`, `selected_objects_v2_7.py`, `position_cursor_probe_v3_2.py`, `selection_coordinate_v3_1.py`.

Não foram descobertos endereços novos; não há alteração do mapping.

## Fluxo
1. Operador, **em partida local e offline**, seleciona manualmente **uma** unidade.
2. O código observa seleção estável com o único Object ID esperado.
3. Lê posição candidata e confirma identidade/pointer antes de enviar ordem.
4. Somente após `armed=True`, `offline_confirmed=True` e `allow_candidates=True`, envia **um** clique direito na coordenada *client* especificada.
5. Reobserva seleção, identidade e deslocamento candidato em prazos limitados. Não envia retries.

A posição e o alvo **não** são coordenadas do mundo provadas. O clique pode provocar interação/ataque/coleta dependendo da superfície clicada. Recomenda-se mapa vazio, unidade isolada e destino livre longe de UI. Não execute em partidas multiplayer ou com oclusão/diálogo.

## Invocação controlada (Python)
```python
from aoe2hdcontrol.object_api import HDObjectAPI, WindowsProcessReader
from aoe2hdcontrol.movement_v3_4 import experiment
from aoe2hdcontrol.catalog import mapping_dir
import json

pid = 1234        # substituir pelo PID correto
object_id = 2188  # substituir pelo Object ID desta sessão
with WindowsProcessReader(pid) as reader:
    api = HDObjectAPI(reader, mapping_dir(), allow_candidates=True)
    report = experiment(api, pid=pid, object_id=object_id,
                        client_x=600, client_y=400,
                        armed=True, offline_confirmed=True)
print(json.dumps(report, indent=2))
```

**Atenção:** coordenadas *client* são relativas ao canto superior esquerdo da área cliente do jogo, não da tela. Não execute o exemplo sem substituir os valores, verificar o processo e selecionar a unidade. O jogo precisa estar em primeiro plano no momento do clique; o PID não autentica a versão do executável.

## Evidência e limitações
O estado `candidate_displacement_observed` indica apenas variação acima do limiar em offsets candidatos. **Não** prova execução do comando, destino alcançado, causalidade, propriedade de unidade, nem validade geral da seleção. Se a identidade/seleção variar, interrompe a observação. Falha parcial de `SendInput` pode deixar um estado de botão incerto: não há retry automático. O operador deve interromper o ensaio.

Testes automatizados: `python -m unittest tests.test_movement_v3_4 -v` ou `python -m unittest discover -s tests -v`. São simulados e não substituem a validação real no HD. Para elevar o status de CMD-001 no futuro, exigem-se duas sessões independentes, hash da build, coleta de JSON antes/depois, casos negativos e análise no mapping.
