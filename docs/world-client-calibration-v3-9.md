# v3.9 — calibração experimental mundo → pixel cliente

## Método e limites
**Hipótese:** com câmera fixa e projeção local aproximadamente afim, o pixel dos pés de uma unidade pode ser ajustado a partir de suas coordenadas candidatas (Object+0x3C/0x40).

`client_x = a*x_world + b*y_world + c`; `client_y = d*x_world + e*y_world + f`.

**Três unidades visíveis, paradas e não colineares** definem os 6 coeficientes; uma **quarta unidade distinta** é usada exclusivamente para validação. Dois pontos sozinhos não determinam uma transformação afim geral. O erro de validação é em pixels, limite operacional preliminar 20 px (não prova de equivalência). As posições cliente dos *pés no chão* são indicadas manualmente via cursor, não por detecção de objetos na imagem. Não há clique, despacho, escrita de memória nem `UnitsMove`.

**Câmera:** manter COMPLETAMENTE IMÓVEL durante as quatro capturas. Como não há prova de calibração da câmera, o script não pode verificar automaticamente mudança de câmera: o relatório marca `operator_reported_only`. Após qualquer rolagem, zoom ou mudança de resolução, descarte a calibração e recomece com outro `--output`. A posição do cursor é registrada enquanto a janela do jogo está em primeiro plano; `read_cursor_coordinates` fornece pixels CLIENTE.

## Passos Windows (8 segundos por captura)
1. Certifique-se de que quatro aldeões próprios estejam VISÍVEIS, parados, distribuídos em duas direções não colineares; câmera imóvel. Faça este ensaio em partida local/offline. IDs só servem na sessão.
2. Selecione SOMENTE o primeiro aldeão. Execute `python -m aoe2hdcontrol.world_client_v3_9 capture`; durante 8 segundos volte ao jogo e deixe o cursor sobre o ponto de contato dos **pés no solo** do mesmo aldeão. **Não clique.**
3. Repita `capture` para mais dois aldeões distintos, alternando a seleção individual **sem mover a câmera**, e mais uma vez para o quarto aldeão, reservado para validação independente.
4. Execute `python -m aoe2hdcontrol.world_client_v3_9 fit`.
5. Inspecione `json/world_client_v3_9.json`: pontos de treino, `calibration.coefficients_candidate`, `training_error_px` e `validation_error_px`.

**Atenção:** ao selecionar cada unidade com mouse, faça-o sem mover a câmera e verifique que o cursor capture a posição dos pés, não o centro do sprite. Os quatro pontos devem ser não colineares, e o quarto deve ficar em uma área próxima aos três primeiros para evitar extrapolação. Evite mover unidades selecionadas ou deixá-las em tarefas.

Se `fit` indicar erro alto, revise principalmente a câmera, o pixel dos pés, movimentação e identidade da unidade, além de projeção não afim/efeitos de terreno.

## Evidência e referências cruzadas
- `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md`: OBJ-004 permanece candidato e CMD-001 bloqueado, sem compatibilidade de ABI entre DE e HD.
- `AoE2HD.mapping/docs/mapa.md`: fonte canônica de layouts/offsets/IDs; não foram promovidos offsets candidatos.
- `AoE2HD.control` v3.2, v3.4, v3.8: seleção estável, leitura da posição candidata e cursor no cliente.
- v3.8 registrou coordenadas e distância estáveis com um aldeão fora da tela; isso **não** estabelece transformada mundo→tela.
- O mapeamento calculado só vale para a câmera e resolução testadas; sem validação automática da câmera e sem validação da projeção, nunca usar para despacho de comandos.

Testes: `python -m unittest discover -s tests -p "test_world_client_v3_9.py" -v`.
