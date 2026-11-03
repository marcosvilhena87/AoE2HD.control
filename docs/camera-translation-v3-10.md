# v3.10 — compensação candidata de deslocamento da câmera

## Hipótese
A transformação afim obtida na v3.9 (`pixel = M*world + t0`) continua válida após deslocar a câmera **apenas por translação no plano da tela**. Com a câmera alterada, um ponto conhecido fornece a nova translação residual `delta = pixel_observado_anchor - predict_v39(world_anchor)`. Aplicamos o mesmo delta a uma **segunda referência independente**, que não contribuiu para estimá-lo; o erro de previsão no segundo ponto refuta ou apoia a hipótese.

O procedimento é de **leitura somente**, sem mouse click, deslocamento automático, escrita de memória ou `UnitsMove`. Nem o deslocamento da câmera nem sua estabilidade são verificados por memória: **são informados pelo operador**.

## Pré-requisitos
- Partida local/offline, mesmo PID, mesmos aldeões e mesma resolução da v3.9.
- Arquivo `json/world_client_v3_9.json` íntegro com quatro pontos e `calibration.validation_within_threshold=true` e `status=candidate_fit_passed_heldout`.
- Não movimentar os aldeões após a v3.9.
- Deslocar a câmera uma vez, de modo que **pelo menos dois aldeões originais permaneçam visíveis** na nova vista; depois, manter a câmera fixa até finalizar as duas capturas.
- Os dois IDs precisam ser distintos e constar entre os quatro do arquivo original; a segunda unidade é validação independente.
- Capturar cursor junto ao **ponto de contato dos pés com o chão**, sem clique.

## Execução no PowerShell (8 segundos em cada captura)
1. Desloque a câmera, selecione e deixe visível um dos aldeões originais. Execute:
   `python -m aoe2hdcontrol.camera_translation_v3_10 anchor`
   Volte ao jogo, coloque o cursor nos pés do aldeão selecionado e NÃO clique.
2. Sem mover a câmera, selecione um **outro aldeão original** e execute:
   `python -m aoe2hdcontrol.camera_translation_v3_10 check`
   Volte ao jogo e aponte para os pés dele sem clicar.
3. Execute:
   `python -m aoe2hdcontrol.camera_translation_v3_10 evaluate`

Relatório separado: `json/camera_translation_v3_10.json`; o arquivo v3.9 **não será alterado**. Uma hash SHA-256 dos bytes da v3.9 protege a associação entre as capturas e a mesma calibração. A v3.10 bloqueia PID diferente, Object ID desconhecido, assinatura de identidade inconsistente, movimento candidato da unidade acima de 0,03, captura duplicada, ordem invertida ou ponto não finito.

Os resultados possíveis são `candidate_translation_passed_heldout`, `candidate_translation_failed_heldout`, `candidate_no_measurable_shift`. Limites exploratórios: erro da validação ≤ 20 px e deslocamento detectável ≥ 3 px. O valor final NÃO autoriza geração de cliques automáticos.

## Interpretação
- Erro pequeno: favorece a hipótese **local** de que a câmera apenas transladou a projeção; não estabelece equivalência geral.
- Erro grande: possível rolagem/zoom adicional entre capturas, imprecisão do cursor nos pés, mudança de resolução, movimento de objeto, projeção não linear/oclusão ou calibração inicial insuficiente.
- Valor quase zero de deslocamento: a câmera não foi deslocada o bastante para testar hipótese.
- A "validação" depende de apontamentos manuais e não captura simultânea dos dois marcadores: não detecta movimentação da câmera entre as duas leituras.

Fontes: `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md` (OBJ-004 candidato; CMD-001 bloqueado), `AoE2HD.mapping/docs/mapa.md` (status de identidade e posição ainda candidato), `AoE2HD.control` v3.9 `world_client_v3_9.py`. O experimento v3.9 teve erro independente ~2,901 px em apenas uma câmera.

Testes: `python -m unittest discover -s tests -p "test_camera_translation_v3_10.py" -v`.
