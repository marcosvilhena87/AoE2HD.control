# v3.3.17 — Experimento de identificação dinâmica por movimento manual

## Objetivo e hipótese

Verificar se o **mesmo Object ID** apresenta deslocamento de memória (world)
coerente com o deslocamento visual da unidade após uma ordem dada **manualmente
pelo operador**. Um segundo Object ID imóvel funciona como controle negativo.
O resultado é **candidato de consistência dinâmica**, não prova absoluta da
identidade, layout canônico ou autorização para seleção programática.

Referências consultadas: matriz HD v3 em `AoE2HD.aoe2control` (OBJ-004,
posição candidata), `AoE2HD.mapping/docs/criterios.md` (offsets e evidências
de sessão), `AoE2HD.control` (v3.3.2, v3.3.11–v3.3.17). Nenhum endereço,
RVA ou offset novo é acrescentado.

## Procedimento (jogo local, sem automação de comandos)

Pré-requisitos: seis âncoras + dez holdouts numéricos v3.3.15 aprovados,
`json/saida_v3_3_15/fit_v3_3_15.json` sem modificações, jogo no mesmo
tamanho de janela, duas unidades visualmente identificáveis **na mesma
tela**, uma delas capaz de mover-se. Não use a unidade do controle como alvo.
Não alterar câmera/zoom entre capturas, manter unidades visíveis, não
permitir que o controle se mova. Os IDs da sessão anterior **não são
automaticamente válidos em nova sessão**: consulte novos IDs do processo.

1. Obtenha o PID atual:

```powershell
$gamePid = (Get-Process 'AoK HD').Id
$targetId = 2519   # substitua por Object ID atual de uma unidade movel
$controlId = 2520  # substitua por Object ID atual de outra unidade imovel
```

2. Capture uma **nova imagem de referência** mantendo a câmera parada:

```powershell
python -m aoe2hdcontrol camera-reference-v3-3-12 `
  --pid $gamePid --delay 8 `
  --image json/dynamic_camera_ref_v3_3_17.bmp
```

3. Registre `target_before` e `control_before` com a câmera fixa.
O comando demora oito segundos para permitir retornar ao jogo e posicionar
o cursor na base da unidade. Não clique durante a coleta.

```powershell
$states = @(
    @{ name="target_before"; id=$targetId },
    @{ name="control_before"; id=$controlId }
)
foreach ($state in $states) {
    $name = $state.name
    Read-Host "Coloque o cursor na unidade $($state.id), ENTER"
    python -m aoe2hdcontrol capture-camera-guarded-v3-3-12 `
      --pid $gamePid --id $state.id --delay 8 `
      --reference json/dynamic_camera_ref_v3_3_17.bmp `
      --image-before "json/dynamic_${name}_before.bmp" `
      --image-after "json/dynamic_${name}_after.bmp" `
      --allow-candidates --output "json/dynamic_${name}.json"
    if ($LASTEXITCODE -ne 0) { throw "Capture $name failed" }
}
```

4. **Somente agora**, ordene manualmente a movimentação da unidade alvo,
usando a interface do próprio jogo. Mova-a o suficiente para alcançar pelo
menos **30 pixels** de deslocamento na tela. Espere que pare. Não desloque a
câmera, nem a unidade de controle. Capture os estados após o movimento:

```powershell
$states = @(
    @{ name="target_after"; id=$targetId },
    @{ name="control_after"; id=$controlId }
)
foreach ($state in $states) {
    $name = $state.name
    Read-Host "Com unidade parada, posicione o cursor na base: $name, ENTER"
    python -m aoe2hdcontrol capture-camera-guarded-v3-3-12 `
      --pid $gamePid --id $state.id --delay 8 `
      --reference json/dynamic_camera_ref_v3_3_17.bmp `
      --image-before "json/dynamic_${name}_before.bmp" `
      --image-after "json/dynamic_${name}_after.bmp" `
      --allow-candidates --output "json/dynamic_${name}.json"
    if ($LASTEXITCODE -ne 0) { throw "Capture $name failed" }
}
```

5. Gere o manifesto, usando caminhos relativos à pasta `json`:

```powershell
$fit = "json/saida_v3_3_15/fit_v3_3_15.json"
$ref = "json/dynamic_camera_ref_v3_3_17.bmp"
$manifest = @{
    schema="hd-dynamic-identity-v3.3.17"
    operator_note="Manual movement of target; control deliberately stationary; camera fixed by operator"
    movement_method="manual_in_game"
    pid=[int]$gamePid
    target_id=[int]$targetId
    control_id=[int]$controlId
    fit_file="saida_v3_3_15/fit_v3_3_15.json"
    fit_sha256=(Get-FileHash $fit -Algorithm SHA256).Hash.ToLower()
    reference_image="dynamic_camera_ref_v3_3_17.bmp"
    reference_sha256=(Get-FileHash $ref -Algorithm SHA256).Hash.ToLower()
    captures=@{
        target_before="dynamic_target_before.json"
        control_before="dynamic_control_before.json"
        target_after="dynamic_target_after.json"
        control_after="dynamic_control_after.json"
    }
    thresholds=@{
        target_min_client_px=30
        target_min_world=0.25
        control_max_client_px=8
        control_max_world=0.2
        delta_max_error_px=12
    }
}
$manifest | ConvertTo-Json -Depth 15 |
    Set-Content "json/dynamic_manifest_v3_3_17.json" -Encoding UTF8
```

6. Execute a análise **offline**:

```powershell
python -m aoe2hdcontrol.dynamic_identity_v3_3_17 `
  --manifest json/dynamic_manifest_v3_3_17.json `
  --output-dir json/dynamic_result_v3_3_17
```

A saída contém `dynamic_report.json`, e, se todos os gates passarem,
`target_motion_review.png`. Vermelho: ponto anterior do alvo; verde: ponto
posterior; amarelo: vetor na imagem do estado final.

## Gates e limitações

- Exatamente quatro capturas protegidas v3.3.12, dois IDs distintos
  preservados no antes/depois e um único PID.
- `candidate_camera_static` em três comparações de cada captura e
  comparação robusta do BMP de cada estado com a referência.
- Integridade SHA256 do ajuste congelado e referência de câmera. Sem
  recalcular coeficientes; apenas diferenças da matriz linear afim.
- Movimento alvo visível ≥30 px e em mundo ≥0,25; controle ≤8 px
  na tela e ≤0,2 no mundo; erro entre deslocamento projetado e observado
  ≤12 px (limiares experimentais configuráveis).
- Os três indicadores da unidade podem mudar quando o cursor for
  posicionado sobre outro objeto. Não atribuir identidade comprovada apenas
  pela relação de deslocamento; repetir com diferentes unidades, controles,
  direções e sessões, com revisão visual independente.
- `candidate_dynamic_consistency_passed` preserva em todos os casos
  `validated_for_selection=false`, `selection_dispatch=not_dispatched`,
  `memory_write=false`.
- O detector visual analisa quadros amostrados, não movimento contínuo.
- Capturas/matrizes são locais e não são enviadas ao GitHub. Não comitar
  BMPs, endereços absolutos de sessão nem identificadores arbitrários
  como se fossem offsets canônicos.

Testes: `python -m unittest tests.test_dynamic_identity_v3_3_17 -v`
e regressão `python -m unittest discover -s tests -v`.
