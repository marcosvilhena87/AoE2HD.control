# v3.2 — posição candidata da unidade e cursor

A v3.2 registra, **sem escrita no jogo**, duas medições independentes:

1. Posição da unidade, nos campos candidatos `Object+0x3C` (float32 X)
   e `Object+0x40` (float32 Y), **não validados para unidades móveis**.
2. Posição do cursor do Windows, global (screen) e relativa à área cliente
   (client), somente enquanto a janela pertencente ao PID está em primeiro plano.

**Ainda não foi identificado um ponteiro validado para coordenadas do cursor
dentro do mundo do jogo.** Coordenadas Windows `client` NÃO são
coordenadas `world`. Nenhuma conversão isométrica foi presumida.
A unidade continua identificada por Object ID somente na sessão.

## Experimento no PowerShell

```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
git fetch origin
git switch feat/v3-2-world-position-cursor-probe
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id

# Antes de executar, descubra e atualize o ID da unidade pela selected-v2-7.
# 2630 é somente um exemplo de sessão anterior.
python -m aoe2hdcontrol probe-position-cursor-v3-2 --pid $gamePid --id 2630 --samples 12 --interval 0.5 --allow-candidates --output position_cursor_v3_2.json
$r = Get-Content .\position_cursor_v3_2.json -Raw | ConvertFrom-Json
$r.readings | ForEach-Object {
    [pscustomobject]@{
        amostra=$_.sample
        unidade_x=$_.unit.candidate_world_x
        unidade_y=$_.unit.candidate_world_y
        cursor_x=$_.cursor.client.x
        cursor_y=$_.cursor.client.y
        jogo_ativo=$_.cursor.game_foreground
    }
} | Format-Table
```

Cinco segundos antes do início, volte ao jogo. Primeiro deixe unidade
parada e mova somente o cursor; depois mova a unidade (sem alterar a câmera
se possível). Observe se X/Y da unidade acompanham a movimentação.
Não pressione botões de automação; este comando **não envia cliques**.

O experimento não prova vínculo com câmera ou mapa. Para identificar
coordenadas de cursor *dentro* do jogo será necessário investigar e
catalogar candidatos adicionais em `AoE2HD.mapping`, exigindo contrastes
cursor parado/móvel, câmera parada/móvel, unidades paradas/móveis, diferentes
zooms e sessões. Até lá, `game_cursor_world_coordinates=unknown`.

## Proveniência
- `AoE2HD.control/aoe2hdcontrol/object_validation_v1_3.py` já
  registrava `0x3C/0x40` como posições candidatas em certos edifícios;
  esta versão investiga leitura para Object IDs móveis e não promove offsets.
- `AoE2HD.mapping` é a fonte canônica de mapeamentos;
  nenhuma nova posição de memória foi declarada validada.
- `AoE2HD.aoe2control` mantém a matriz de compatibilidade DE/HD sem
  equivalência funcional presumida.

## Limitações
Sem hash/versão automática do executável, sem proveniência de câmera, sem
rastreamento de eventos e sem vínculo identificado com cursor world;
leituras sequenciais não são atômicas. Use apenas em partidas offline.
