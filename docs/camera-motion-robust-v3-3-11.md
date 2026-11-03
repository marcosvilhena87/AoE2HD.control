# v3.3.11 — Detecção robusta de movimento de câmera

Comparação **offline** de duas capturas com **ORB + correspondências mútuas +
RANSAC**. Estima o deslocamento global por mediana dos vetores dos inliers;
rejeita resultados com cobertura espacial pequena, ambiguidade, escala/rotação
incompatíveis ou resíduos elevados. Não exige marcos manuais.

O método anterior `check-camera-v3-3-10` continua disponível.
**Não escreve memória nem controla mouse ou teclado.**

## Dependências opcionais

```powershell
python -m pip install opencv-python numpy Pillow
```

## Executar com as duas capturas da unidade 2535

```powershell
python -m aoe2hdcontrol check-camera-robust-v3-3-11 `
  --before json/visual_nova_2535.bmp `
  --after json/visual_nova_2535_b.bmp `
  --output json/camera_2535_v3_3_11.json

$r=Get-Content .\json\camera_2535_v3_3_11.json -Raw | ConvertFrom-Json
$r | Select-Object status,good_matches,inliers,inlier_ratio,
    dx_px,dy_px,median_residual_px,coverage_cells,scale,rotation_deg |
    Format-List
```

O deslocamento é definido como **posição na imagem after menos posição na
imagem before**. `camera_moved` exige consenso geométrico suficiente e
magnitude superior a 2 px; `candidate_camera_static` indica alinhamento
apenas dos dois instantes; `camera_unverified` indica evidência insuficiente.

Não há valores de deslocamento predefinidos para a 2535: interprete somente o
JSON gerado a partir das imagens. O deslocamento entre duas imagens não prova
que toda a sequência permaneceu imóvel, não confirma Object IDs nem corrige
a projeção.

## Bloqueio do lote

```powershell
python -m aoe2hdcontrol gate-camera-robust-v3-3-11 `
  --camera json/camera_2535_v3_3_11.json `
  --batch json/lote_v3_3_7_recente.json `
  --output json/controle_camera_lote_v3_3_11.json
```

Sempre retorna `validated_for_selection=false`. Se houver movimento ou
evidência inconclusiva, `blocked`; caso apenas os dois extremos estejam
alinhados, `manual_intermediate_review_required`.

Para testar:

```powershell
python -m unittest discover -s tests -v
```

Teste de deslocamento sintético exige OpenCV e Pillow e é pulado na ausência
das dependências. Se não funcionar com imagens reais, inspecione primeiro
inliers, distribuição espacial e resíduos; não relaxe automaticamente os
limiares apenas para obter aprovação.
