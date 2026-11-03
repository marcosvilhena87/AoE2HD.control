# v3.3.9 — correspondência visual e resíduos robustos (offline)

## Objetivo

A v3.3.9 não reconhece visualmente unidades e **não** atribui automaticamente
causas para a divergência da 2535. O operador confere as imagens BMP, registra
uma declaração explícita de identidade e câmera em **manifesto separado** e
compara estatísticas completas versus o subconjunto revisado. Originais não
são modificados e todos os outliers permanecem no relatório.

## 1. Criar manifesto inicial

Exemplo válido e conservador, sem alegar conferência visual:

```powershell
$auditoria = Get-Content .\json\auditoria_residuos_v3_3_8.json -Raw | ConvertFrom-Json
$manifesto = @{
    schema = 'hd-visual-reviews-v3.3.9'
    reviews = @(
        $auditoria.samples | ForEach-Object {
            @{
                report = $_.file
                identity = 'uncertain'
                camera = 'uncertain'
                reference = 'unknown'
                reason = 'Aguardando conferencia do BMP'
                bmp = ''
                reviewer = ''
            }
        }
    )
}
$manifesto | ConvertTo-Json -Depth 10 |
    Set-Content .\json\revisoes_v3_3_9.json -Encoding UTF8
```

## 2. Revisar manualmente

Edite somente `revisoes_v3_3_9.json`. Para cada `report`, use:

* `identity`: `confirmed`, `rejected` ou `uncertain`
* `camera`: `confirmed_static`, `changed` ou `uncertain`
* `reference`: `unit_base`, `other` ou `unknown`
* `reason`: evidência e motivo concretos
* `bmp`: caminho correspondente, para rastreabilidade
* `reviewer`: nome ou identificador do responsável

Marque como confirmado apenas o que foi efetivamente conferido. Uma captura
com identidade confirmada, câmera afirmada estática e referência `unit_base`
entra no subconjunto de **revisão elegível**. Isso é uma afirmação do operador,
não uma confirmação automática da imagem. Se não houver segurança de que o
enquadramento ficou estável, mantenha `camera=uncertain`.

## 3. Executar

```powershell
python -m aoe2hdcontrol review-correspondence-v3-3-9 `
  --audit json/auditoria_residuos_v3_3_8.json `
  --reviews json/revisoes_v3_3_9.json `
  --output json/resultado_revisao_v3_3_9.json

$r=Get-Content .\json\resultado_revisao_v3_3_9.json -Raw | ConvertFrom-Json
$r.all_observations | Format-List
$r.review_eligible_only | Format-List
$r.flagged_or_unreviewed | Format-List
$r.repeated_objects | Format-Table object_id,n,max_measured_spread_px
$r.region_by_predicted_y | Format-List
$r.robust_trends_all | Format-List
```

Inclui análise descritiva de resíduos por tercis verticais da tela
(superior/intermediário/inferior) e tendências robustas Theil–Sen de dx vs X e
dy vs Y. **Não** recalibra nem prova distorção. A estatística do subconjunto
revisado pode sofrer viés de seleção; sempre compare com a amostra total.

O caso 2535 deve manter todas as observações ainda disponíveis e sua
dispersão, sem escolher automaticamente a mais favorável. Não existem
cliques, automação de seleção, escrita de memória ou aprovação de câmera
implementados nesta versão.
