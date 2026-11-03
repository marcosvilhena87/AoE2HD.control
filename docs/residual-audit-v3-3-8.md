# v3.3.8 — auditoria dos resíduos e correspondência visual

Lê **somente JSONs v3.3.6** e gera um JSON de auditoria mais um SVG
representando a área cliente (1536×864 por padrão). Círculo vazado = previsto;
ponto sólido = medido; segmento = vetor de resíduo (medido menos previsto);
vermelho = erro acima de 25 px. O SVG é **mapa de coordenadas**, não uma captura
do jogo, nem prova de identidade de objetos na imagem.

## Executar com as dez unidades e todas as medições disponíveis da 2535

Não inclua o mesmo caminho duas vezes e não substitua resultados anteriores
silenciosamente. Os nomes `_b` podem ter sido sobrescritos em testes passados;
verifique seu conteúdo real antes de concluir sobre a cronologia.

```powershell
$ids = @(2566,2561,2611,2613,2535,2626,2546,2625,2583,2547)
$reports = @($ids | ForEach-Object { ".\json\validacao_nova_$_.json" })
$extra = ".\json\validacao_nova_2535_b.json"
if (Test-Path $extra) { $reports += $extra }
foreach ($p in $reports) { if (-not (Test-Path $p)) { throw "Arquivo ausente: $p" } }

python -m aoe2hdcontrol audit-residuals-v3-3-8 `
  --reports $reports --client-width 1536 --client-height 864 `
  --threshold-px 25 `
  --output json\auditoria_residuos_v3_3_8.json `
  --svg json\mapa_residuos_v3_3_8.svg

Start-Process ".\json\mapa_residuos_v3_3_8.svg"
```

Abra os BMPs correspondentes para conferir manualmente o alvo e a câmera.
Uma diferença entre posições do cursor não determina automaticamente se
houve erro de projeção, troca de objeto, deslocamento da câmera ou diferença
no ponto da base visual. Anote essa conclusão separadamente.

O JSON inclui todas as medições, IDs repetidos, dispersão máxima do cursor
por objeto, erros assinados `dx/dy`, média, RMSE, máximos e inclinações
descritivas dos resíduos. **Nenhum ajuste de calibração ou clique é realizado**.
As inclinações são apenas pistas exploratórias; não provam distorção.
