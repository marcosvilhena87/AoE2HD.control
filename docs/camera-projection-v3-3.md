# v3.3 — calibração empírica mundo → tela, câmera estacionária

A v3.3 **não encontrou nem inventou offsets de câmera ou de coordenadas
de cursor no mundo**. Ela ajusta uma transformação afim bidimensional a
pontos correspondentes conhecidos da unidade no mundo e na área cliente
da janela do jogo. O ajuste é EXCLUSIVAMENTE experimental e deixa de ser
válido quando a câmera, janela, resolução ou zoom são alterados.

## Coleta de âncoras

1. Escolha pelo menos **três unidades ou construções em locais distintos
   e não colineares**, visíveis simultaneamente. Com câmera parada, obtenha
   seus Object IDs e coordenadas candidatas (Object+0x3C/0x40; v3.2).
2. Para cada objeto, posicione o cursor sobre seu centro e capture a
   coordenada **relativa à área cliente**, com a janela em foco, usando
   `probe-position-cursor-v3-2`. Somente anote a amostra em que o cursor
   esteja sobre o centro visual do objeto. Não confunda screen com client.
3. Monte um CSV com colunas exatas:
   `world_x,world_y,client_x,client_y`. Cada linha precisa
   corresponder ao **mesmo objeto** e à **mesma configuração de câmera**.

Exemplo sintético para testar a CLI (NÃO é medição do jogo):

```csv
world_x,world_y,client_x,client_y
0,0,100,50
5,0,110,55
0,7,93,57
4,3,105,57
```

## CLI

```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
git fetch origin
git switch feat/v3-3-camera-projection-calibration
python -m unittest discover -s tests -v

# Depois de montar ancoras_reais.csv com dados do MESMO enquadramento:
python -m aoe2hdcontrol calibrate-projection-v3-3 --csv ancoras_reais.csv --output calibracao_v3_3.json
Get-Content .\calibracao_v3_3.json -Raw
```

O relatório fornece coeficientes da transformação afim, resíduos
individuais e RMSE em pixels. Três pontos definem um ajuste exato se
não forem colineares, mas **não validam a precisão em outros pontos**.
Colete quatro ou mais âncoras e mantenha pelo menos um ponto de
verificação separado, fora do ajuste. É necessário repetir com câmera
deslocada para investigar a projeção/câmera separadamente.

## Proveniência
- Evidência v3.2 de 30 amostras do objeto 2630 preservada em
  `AoE2HD.mapping/docs/evidencia_movimento_v3_2_2026-11-02.md`.
- `AoE2HD.control` v3.2: posição da unidade experimental;
  cursor da tela/client vindo da API do Windows.
- `AoE2HD.aoe2control` matriz v3: sem equivalência presumida da DE.

**Não habilita seleção automática por ID**, não envia clique, não escreve
memória e não identifica endereço interno de cursor_world ou câmera.
