# v3.3.10 — proteção contra deslocamento de câmera

**Read-only/offline**. Compara dois BMPs existentes em marcos **estáticos**
escolhidos pelo operador. Não acessa o processo AoK HD.exe, não envia clique
nem escreve memória. Necessita `Pillow` (`python -m pip install Pillow`).

O método procura cada retalho em uma janela (padrão ±60px), compara intensidades,
exige textura suficiente, boa similaridade, um pico não ambíguo e concordância
entre três ou mais marcos. A busca ocorre em passos de 2px; deslocamentos
estimados são aproximados. Use regiões de **terreno que permaneçam estáticas**,
afastadas de HUD, animações, unidades e bordas. Marcar um objeto móvel como
referência pode produzir diagnóstico falso.

## Preparação

Use dois screenshots capturados em instantes relevantes sob a mesma resolução.
As capturas da unidade 2535 são candidatas para investigação, não prova de
estabilidade da câmera. Sem evidência visual suficiente, não declare câmera
estática.

Escolha 3–12 pontos em áreas visivelmente estáticas, distribuídos pelo mapa,
e com margem de pelo menos 74 pixels em relação às bordas se a busca for 60px.

Exemplo de **formato** (coordenadas ilustrativas; substitua por pontos realmente
identificados nas suas duas imagens):

```json
[
  {"x":250,"y":230},
  {"x":750,"y":380},
  {"x":1210,"y":640}
]
```

Salve em `json/marcos_estaticos_v3_3_10.json`. **Não trate essas
coordenadas ilustrativas como marcos confirmados.**

## Executar a detecção

```powershell
python -m pip install Pillow

python -m aoe2hdcontrol check-camera-v3-3-10 `
  --before json/visual_nova_2535.bmp `
  --after json/visual_nova_2535_b.bmp `
  --anchors json/marcos_estaticos_v3_3_10.json `
  --search-px 60 `
  --output json/camera_2535_v3_3_10.json

$r=Get-Content .\json\camera_2535_v3_3_10.json -Raw | ConvertFrom-Json
$r.observations | Format-Table index,x,y,status,dx,dy,mad
```

`camera_moved`: três ou mais marcos confiáveis concordam em deslocamento
superior a 2px. `candidate_camera_static`: os marcos se alinham aproximadamente
nos **dois instantes**, apenas. `camera_unverified`: textura insuficiente,
correspondência ambígua, divergência entre marcos ou ausência de correspondência.

Retorno 0: apenas correspondência estática candidata; 2: movimento ou
indeterminação; 1: erro de entrada/execução. Não pressupõe correspondência
de cada unidade ao seu Object ID.

## Portão conservador sobre lote da v3.3.7

```powershell
python -m aoe2hdcontrol gate-camera-v3-3-10 `
  --camera json/camera_2535_v3_3_10.json `
  --batch json/lote_v3_3_7_recente.json `
  --output json/controle_camera_lote_v3_3_10.json
```

O portão **nunca** autoriza seleção (`validated_for_selection=false`).
Caso a câmera esteja em movimento ou não verificada, bloqueia; mesmo com
câmera aparentemente estática nos dois BMPs, exige revisão de imagens
intermediárias e identidade visual. O código não reconstrói nem corrige o
deslocamento observado e não recalibra a projeção.
