# v3.1.1 — verificação temporal após um único clique

Objetivo: investigar se o falso negativo inicial da v3.1 foi causado por
leitura antes do processamento da entrada no Age of Empires II HD.

## Contrato
- Um único clique esquerdo pela função `click_at` da v3.1 (SendInput).
- Janela em foco e pertencente ao PID informado; área cliente verificada.
- `--arm` e `--allow-candidates` são obrigatórios.
- Antes do clique, exige snapshot estável e alvo **não selecionado**.
- Leituras nos prazos de 50, 100, 200, 350 e 500 ms, relativos ao retorno
  do despachante de clique; registra duração efetivamente medida,
  consistência e Object IDs em cada tentativa.
- Encerra na primeira correspondência estável; não repete o clique.
- `observed_match` é associação temporal, não prova causalidade.
- Dados de candidatos continuam experimentais; não há escrita de memória.

## Uso (PowerShell)

```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
git fetch origin
git switch feat/v3-1-1-temporal-verification
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id

# Exemplo somente: confirme o Object ID e as coordenadas da sessão atual.
# Selecione uma unidade diferente ANTES de iniciar.
python -m aoe2hdcontrol select-screen-v3-1-1 --pid $gamePid --id 2630 --x 686 --y 461 --allow-candidates --arm --output selection_v3_1_1.json
$r = Get-Content .\selection_v3_1_1.json -Raw | ConvertFrom-Json
$r | Select-Object status, match, first_match_elapsed_ms, dispatch, causality
$r.observations | Select-Object deadline_ms, elapsed_ms, consistency, observed_ids, match
```

No comando, volte ao jogo em até cinco segundos, sem mover a câmera.
A unidade-alvo deve estar visível na posição informada.

## Limites
Os tempos são amostras agendadas, não callbacks do motor do jogo. O instante
do clique é aproximado pelo retorno de SendInput; o tempo de processamento
pode variar. Uma leitura posterior positiva ainda não comprova causalidade;
repetir com controle negativo de coordenada e sem interferência manual.
Não funciona como seleção por Object ID: coordenadas são fornecidas pelo
operador. A matriz de comandos HD da AoE2HD.aoe2control continua sem
comprovação de despacho nativo; mapping v2.6 mantém os offsets candidatos.
