# Experimento v3.8 — duas coordenadas globais candidatas

Objetivo: comparar posições de A e B na memória do AoE II HD antes, durante e depois de mover a câmera, **sem comandos ao jogo**.

## Requisitos e fontes
- AoE2HD.aoe2control: `docs/hd-compatibility-matrix-v3.md`. OBJ-004 é candidato; CMD-001 (UnitsMove) permanece bloqueado.
- AoE2HD.mapping: `docs/mapa.md`, `dados/catalogos/estruturas_memoria.csv`, `dados/catalogos/tipos_genie.csv`; `Object+0x3C/0x40` permanecem candidatos; IDs são específicos da sessão.
- AoE2HD.control: `position_cursor_probe_v3_2.py`, `movement_v3_4.py`, `villager_reference_v3_6.py` e experimento local v3.7, com a posição de um aldeão estável visível/fora da tela/visível.
- Não se infere automaticamente visibilidade ou câmera; o operador confirma ambas.

## Execução, separada em três comandos
Mantenha A selecionado, B parado e os IDs corretos na mesma partida. A captura só começa 8 segundos depois de cada comando.

1. Mostre A e B; execute `python -m aoe2hdcontrol.global_pair_v3_8 1 --a 2114 --b 2115`.
2. Desloque a câmera de modo que **B fique fora da tela**, sem cancelar a seleção de A; execute `python -m aoe2hdcontrol.global_pair_v3_8 2 --a 2114 --b 2115`.
3. Reexiba A e B; execute `python -m aoe2hdcontrol.global_pair_v3_8 3 --a 2114 --b 2115`.

Se A não permanecer selecionado, o programa bloqueia a captura; se o PID, endereço/identidade ou sequência mudar, reinicie pela etapa 1. A câmera precisa estar estabilizada antes da leitura. Se A estiver movimentando-se durante a leitura A/B/A, a captura é rejeitada. O relatório gerado é `json/global_pair_v3_8.json`, com `samples` e `comparisons`.

## Valores registrados
- Posições candidatas de A e B mesmo quando B está fora da tela.
- Vetor `dx=B.x-A.x`, `dy=B.y-A.y`, distância euclidiana A–B e vetor unitário (se distância não nula).
- Ângulo matemático `atan2(dy, dx)` **não é direção/heading validado do motor** (eixos e projeção não confirmados).
- Deslocamento aparente de cada unidade e mudança da distância A–B durante a transição de câmera.
- Assinaturas de identidade de A e B e releitura de A para evitar fotografias inconsistentes.
- Marcadores `camera_position_verified=false`, `offscreen_status=operator_reported`, `world_coordinates_validated=false`, `command_dispatched=false` e `memory_write=false`.

O teste positivo de independência da câmera oferece evidência de *coordenadas do mundo candidatas*, mas não valida que se possa ordenar movimentação no mundo por Object ID. Não existe calibração tela→mundo nesta versão, nem equivalente nativo de UnitsMove.

Testes: `python -m unittest discover -s tests -p "test_global_pair_v3_8.py" -v`.
