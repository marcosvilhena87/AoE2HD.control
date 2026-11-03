# Movement telemetry v3.5 — monitoramento experimental

**Objetivo:** medir deslocamento real entre amostras de posições **candidatas** do mesmo Object ID, até 5 s após uma única tentativa assistida de clique direito.

## Fundamentação
- Referência DE: `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md`; CMD-001 continua sem equivalente nativo HD e OBJ-004 é candidato.
- Fonte canônica: `AoE2HD.mapping/docs/mapa.md` e `dados/catalogos/estruturas_memoria.csv`. Nenhuma alteração de offset.
- Controle: reutiliza guardas de seleção/identidade da v3.4, `selected_objects_v2_7.py` e `position_cursor_probe_v3_2.py`.

## Experimento no Windows
Na pasta `AoE2HD.control`, em partida **local/offline**, selecione **somente o aldeão cujo Object ID foi obtido na sessão atual**, mantenha a janela em primeiro plano e confirme visualmente que o ponto client (600,400) é **solo livre** e não botão, recurso ou construção. O PID e o Object ID abaixo são exemplos e **não** são IDs estáveis.

Crie um script `experimento_v35.py` com:

```python
import json
import time
from pathlib import Path
from aoe2hdcontrol.object_api import WindowsProcessReader, HDObjectAPI
from aoe2hdcontrol.catalog import mapping_dir
from aoe2hdcontrol.movement_v3_5 import monitor

pid = 28628       # atualizar para PID da execução atual
object_id = 2114  # atualizar a partir de selected-v2-7 na MESMA sessão
print("Retorne ao jogo agora; tentativa em 8 segundos.", flush=True)
time.sleep(8)
with WindowsProcessReader(pid) as reader:
    api = HDObjectAPI(reader, mapping_dir(), allow_candidates=True)
    result = monitor(api, pid=pid, object_id=object_id,
                     client_x=600, client_y=400,
                     armed=True, offline_confirmed=True)
path = Path("json/movement_v3_5.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"status": result["status"], "arrival_status": result["arrival_status"],
                  "report": str(path)}, indent=2))
```

Padrão: 200 ms, até 5000 ms, máximo de **um** clique direito, sem retries. Só execute depois de confirmar os valores. A versão do executável ainda depende de verificação externa; `offline_confirmed` é declaração do operador, **não** detecção automática de multiplayer.

## Métricas
Para posições `(x_i,y_i)` e tempos monotônicos `t_i`:
- Distância por passo: `hypot(x_i-x_(i-1), y_i-y_(i-1))`.
- Percurso: soma das distâncias por passo.
- Distância líquida: `hypot(x_i-x_0, y_i-y_0)`.
- Velocidade por passo: distância por passo / delta de tempo em segundos.
- Imobilidade candidata: últimos 3 intervalos de amostragem com deslocamento por intervalo <= 0.03.
- `movement_observed`: percurso >= 0.25 unidades candidatas, sem bloqueios.
- `stationary_observed`: sem deslocamento relevante e com imobilidade persistente.
- `observation_blocked`: alteração de identidade/seleção ou leitura inválida.
- `arrival_unverified`: estado **sempre** não verificado nesta versão, mesmo quando a unidade para.

A saída registra `metrics.samples` com coordenadas, tempos, deslocamentos e velocidades. Se houve movimento e depois parada, `metrics.stationary_observed` também será verdadeiro, enquanto `status` pode continuar `movement_observed`.

## Restrições
- `Object+0x3C/+0x40` não estão validados canonicamente; todos os deslocamentos seguem candidatos.
- A correspondência destino de tela → posição de mundo ainda não foi estabelecida.
- Não confirma chegada, causalidade, aceitação de comando ou comando nativo por ID.
- A seleção deve permanecer única e estável durante o monitoramento, sob pena de interrompê-lo.
- Testes simulados não substituem evidência experimental em duas sessões separadas, com hash da build e JSON bruto.

## Testes
`python -m unittest discover -s tests -p "test_movement_v3_5.py" -v`
