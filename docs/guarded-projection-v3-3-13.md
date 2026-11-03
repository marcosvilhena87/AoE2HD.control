# v3.3.13 — Projeção integrada à captura protegida

Lê JSONs já obtidos pela v3.3.12 e aplica a calibração v3.3.2 **sem
alterar coeficientes**, comparando a posição prevista na tela com a posição
medida do cursor. **Tudo é offline**, sem leitura adicional do processo, clique,
escrita de memória ou autorização de seleção.

## 1. Projetar a medição de câmera estática

```powershell
python -m aoe2hdcontrol project-guarded-v3-3-13 `
  --capture json/2535_guard_01.json `
  --fit json/calibracao_final_v3_3_5.json `
  --client-width 1536 --client-height 864 `
  --threshold-px 25 `
  --output json/2535_projection_guard_01.json
```

A posição do cursor é extraída da âncora sincronizada v3.3.12.
O vetor de resíduo usa **medido menos previsto**. A medição entra na
estatística apenas quando os três checks de câmera estão estáticos,
a captura foi aceita, cursor e âncora são coerentes, a unidade tem
coordenadas finitas e a projeção cai na área cliente. Erro acima de
25 px **não é escondido**: a medição numérica fica disponível com
`within_threshold=false`.

## 2. Repetir no caso bloqueado

```powershell
python -m aoe2hdcontrol project-guarded-v3-3-13 `
  --capture json/2535_guard_02.json `
  --fit json/calibracao_final_v3_3_5.json `
  --client-width 1536 --client-height 864 `
  --output json/2535_projection_guard_02.json
```

Neste cenário `projection_blocked`, `eligible_for_numeric_batch=false`
e `error_px=null`. A captura original bloqueada permanece intacta.

Consulte:

```powershell
$r=Get-Content .\json\2535_projection_guard_01.json -Raw | ConvertFrom-Json
$r | Select-Object status,object_id,predicted_client,measured_client,
   residual,error_px,within_threshold,eligible_for_numeric_batch,
   reference_camera_alignment_with_calibration,validated_for_selection |
   Format-List
```

## 3. Auditar o lote protegido

Inclua arquivos de projeção de **unidades distintas**, com identificadores
não utilizados na calibração/holdout anteriores. Para validar com pelo menos
dez medições novas, forneça os dez arquivos e os IDs excluídos. Exemplos
abaixo demonstram apenas o formato com as duas capturas 2535 (não suficientes):

```powershell
python -m aoe2hdcontrol validate-guarded-v3-3-13 `
  --reports json/2535_projection_guard_01.json json/2535_projection_guard_02.json `
  --exclude-ids 2630 2629 2623 2576 2627 `
  --min-samples 10 --threshold-px 25 `
  --output json/guarded_batch_demo_v3_3_13.json
```

O resumo separa `accepted` e `excluded` com razões de rejeição.
Toda captura bloqueada é preservada fora do cálculo de RMSE; o lote completo
será `inconclusive` caso contenha rejeições, IDs repetidos, amostras
insuficientes, PIDs diferentes ou erro acima do limite. Não reutilize a
unidade 2535 dez vezes para completar o mínimo.

## Limites de validade

As imagens v3.3.12 são verificadas por amostragem; estabilidade entre
quadros é desconhecida. Não há evidência no JSON de que a referência atual
esteja alinhada à câmera usada para ajustar a calibração antiga, nem
verificação automática de identidade visual do Object ID. Por isso o
relatório registra
`reference_camera_alignment_with_calibration=unverified` e
`validated_for_selection=false`. Um `candidate_numeric_batch_passed`
significa **somente** atendimento dos critérios numéricos.
