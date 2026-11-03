# v3.3.15 — Preparação do holdout independente com capturas protegidas

Este procedimento usa os **seis arquivos de captura v3.3.12 já obtidos**:
`2187 2188 2189 2513 2515 2517`. Não altera a câmera, não clica
e não acessa o processo. Exige que as capturas continuem na mesma sessão
(PID 4244 no exemplo) com a referência original preservada.

## 1. Atualizar a branch e auditar o conjunto de treinamento

```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git fetch origin
git switch feat/v3-3-15-camera-session-holdout
git pull --ff-only
python -m unittest discover -s tests -v
```

O adaptador exige os arquivos na ordem especificada, checa o PID único,
Object IDs únicos, os três checks de câmera, o esquema da âncora, a câmera
de referência, o status da captura e os hashes das imagens. Rejeita
treinamento trocado, holdout repetido e captura fora de escopo.

Gere o relatório parcial **sem fingir que os holdouts já existem**:

```powershell
$train = @(2187,2188,2189,2513,2515,2517) |
    ForEach-Object { "json/${_}_guard_v3_3_15.json" }
python -m aoe2hdcontrol.guarded_holdout_v3_3_15 `
  --reference json/camera_ref_2187_v3_3_15.bmp `
  --train $train `
  --session "pid4244-fixed-camera" `
  --note "Capturas protegidas v3.3.12, camera imovel segundo operador" `
  --output json/preparo_holdout_v3_3_15.json
```

O código de saída 2 é **esperado** quando ainda faltam os dez holdouts.
Inspecione `errors`: vazio indica que os seis arquivos de treino
foram reconhecidos, não que a validação esteja pronta.

## 2. Coletar dez novas unidades

Descubra visualmente dez Object IDs distintos, não presentes na lista de
treino, na região visível da câmera atual. Mantenha a câmera imóvel.
Não use ids inventados, unidades fora da tela ou movimento automático
para encontrá-los.

Para cada ID real (por exemplo, substitua SOMENTE `ID_REAL`):

```powershell
$gamePid = (Get-Process 'AoK HD').Id
if ($gamePid -ne 4244) { throw "PID alterado; nao misture sessoes." }
$idReal = ID_REAL
python -m aoe2hdcontrol capture-camera-guarded-v3-3-12 `
  --pid $gamePid --id $idReal --delay 8 `
  --reference json/camera_ref_2187_v3_3_15.bmp `
  --image-before "json/${idReal}_guard_before_v3_3_15.bmp" `
  --image-after "json/${idReal}_guard_after_v3_3_15.bmp" `
  --allow-candidates `
  --output "json/${idReal}_guard_v3_3_15.json"
```

Antes de pressionar Enter, confirme qual unidade corresponde ao Object ID;
durante o atraso de oito segundos, volte ao jogo e aponte sua base. Não
movimente a câmera. Faça uma captura por vez e não sobrescreva evidências.

## 3. Preparar e avaliar

Após obter os dez IDs novos efetivos, forneça seus arquivos guardados
explicitamente:

```powershell
$holdoutIds = @(ID1,ID2,ID3,ID4,ID5,ID6,ID7,ID8,ID9,ID10)
$holdout = $holdoutIds | ForEach-Object { "json/${_}_guard_v3_3_15.json" }
python -m aoe2hdcontrol.guarded_holdout_v3_3_15 `
  --reference json/camera_ref_2187_v3_3_15.bmp `
  --train $train --holdout $holdout `
  --session "pid4244-fixed-camera" `
  --note "Capturas protegidas e IDs atribuídos manualmente" `
  --output json/preparo_holdout_completo_v3_3_15.json
```

O arquivo acima é um envelope de diagnóstico com a propriedade
`manifest`. Se o `status` for `ready_for_evaluation` e `errors`
estiver vazio, exporte o manifesto que o avaliador aceita:

```powershell
$p = Get-Content json/preparo_holdout_completo_v3_3_15.json -Raw | ConvertFrom-Json
if ($p.status -ne "ready_for_evaluation" -or @($p.errors).Count -ne 0) {
    throw "Preparo incompleto ou bloqueado"
}
$p.manifest | ConvertTo-Json -Depth 20 |
    Set-Content json/manifest_holdout_v3_3_15.json -Encoding UTF8
python -m aoe2hdcontrol.calibration_session_v3_3_15 `
  --manifest json/manifest_holdout_v3_3_15.json `
  --output-dir json/resultado_holdout_v3_3_15 `
  --threshold-px 25 --min-holdouts 10
```

**Resultados possíveis:** `candidate_session_numeric_passed` (somente
triagem numérica) ou `blocked`. São exigidos todos os 16 IDs únicos,
todos os checks de câmera e integridade das evidências.

### Limitações

- A rotina ainda não prova identidade visual entre Object ID e personagem.
- Comparações ORB/RANSAC mostram **fotogramas amostrados**, não câmera
  imóvel continuamente. Dados sintéticos não substituem o experimento.
- O manifesto guarda os SHA-256 das imagens e dos relatórios originais;
  o avaliador detecta alteração dos arquivos após o preparo.
- Calibração com seis amostras já vista pelo operador pode induzir viés;
  não ajuste parâmetros depois de examinar as dez amostras de holdout.
- A saída de seleção permanece permanentemente
  `validated_for_selection=false`, `selection_dispatch=not_dispatched`.
- O diretório de resultado deve estar vazio ou inexistente; não sobrescreva.
