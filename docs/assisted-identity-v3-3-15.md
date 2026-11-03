# v3.3.15 — confirmação visual assistida do Object ID

A captura protegida v3.3.12 garante apenas que houve três comparações de
câmera amostradas, não que o cursor corresponde a um Object ID. Esta versão
oferece um protocolo **manual, offline, somente leitura e fail-closed**.

1. Prepare uma imagem com mira amarela nas coordenadas capturadas e painel
   ampliado do entorno. O cursor gráfico pode não aparecer na captura GDI.
2. O operador analisa a tela original e declara explicitamente `confirmed`,
   `rejected` ou `uncertain`. **Não marque confirmado se houver dúvida.**
3. Repita em outra captura da **mesma unidade isolada**, com câmera fixa.
4. Um auditor compara os dois registros com hashes SHA-256, estabilidade
   da câmera ORB+RANSAC, posição mundial, deslocamento do cursor e igualdade
   de Object ID/PID. Ele nunca afirma prova automática de identidade.

## 0. Experimento recomendado

Não reutilize a captura 2535 de cursor (1003, 552) para confirmação: a imagem
mostra várias unidades próximas, sem prova de que o ID 2535 foi localizado.

Primeiro confirme a identidade por um procedimento externo ao OCR/código:
isole uma unidade visualmente (controle manual do jogador), confira a
correspondência por alteração controlada e reversível de seu estado no jogo
ou investigação externa de identidade. O simples fato de haver uma unidade
sob a mira **não revela o ID**. Não use revisão confirmada apenas por palpite.

Mantenha o jogo e câmera no mesmo enquadramento; registre duas capturas com
`capture-camera-guarded-v3-3-12` e novos caminhos:

```powershell
$gamePid=(Get-Process 'AoK HD').Id
python -m aoe2hdcontrol capture-camera-guarded-v3-3-12 `
  --pid $gamePid --id 2535 --delay 20 --allow-candidates `
  --reference json/camera_ref_sessao_01.bmp `
  --image-before json/2535_isolada_pre_A.bmp `
  --image-after json/2535_isolada_post_A.bmp `
  --output json/2535_isolada_A.json
```

Repita com `_B` nos três nomes e posicione o cursor sobre a base da **mesma**
unidade.

## 1. Produzir os painéis de revisão

```powershell
python -m aoe2hdcontrol prepare-identity-v3-3-15 `
  --capture json/2535_isolada_A.json `
  --overlay json/2535_isolada_A_review.png `
  --output json/2535_isolada_A_pending.json

python -m aoe2hdcontrol prepare-identity-v3-3-15 `
  --capture json/2535_isolada_B.json `
  --overlay json/2535_isolada_B_review.png `
  --output json/2535_isolada_B_pending.json

Start-Process .\json\2535_isolada_A_review.png
Start-Process .\json\2535_isolada_B_review.png
```

## 2. Registrar a revisão humana

Somente se a identidade tiver sido comprovada independentemente, a unidade
estiver isolada e o cursor estiver sobre a base:

```powershell
python -m aoe2hdcontrol review-identity-v3-3-15 `
  --input json/2535_isolada_A_pending.json `
  --identity confirmed --isolated --cursor-on-target `
  --reviewer "operador" `
  --note "Registrar como a identidade foi corroborada independentemente" `
  --output json/2535_isolada_A_reviewed.json
```

Repita para B com `B_pending` e `B_reviewed`. Se a identidade não estiver
estabelecida, use `--identity uncertain` sem flags `--isolated` ou
`--cursor-on-target`; a revisão não será aceita para auditoria positiva.

## 3. Auditoria de duas capturas

```powershell
python -m aoe2hdcontrol audit-identity-repeat-v3-3-15 `
  --first json/2535_isolada_A_reviewed.json `
  --second json/2535_isolada_B_reviewed.json `
  --cursor-tolerance-px 15 `
  --world-tolerance 0.02 `
  --output json/2535_isolada_audit_v3_3_15.json
```

Leia os campos `status`, `reasons`, `world_distance`,
`cursor_distance_px` e `camera_check`. Em hipótese alguma
`candidate_operator_correspondence_repeatable` autoriza seleção automática,
pois o programa não identifica visualmente o Object ID.

Todos os caminhos de saída devem ser novos. Guardam-se os arquivos originais,
a imagem de revisão e declarações do operador para auditoria posterior.
