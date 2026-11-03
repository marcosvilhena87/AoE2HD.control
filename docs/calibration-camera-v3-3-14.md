# v3.3.14 — Vincular calibração à câmera de origem

Camadas **offline** e **somente leitura**. A referência de câmera da
calibração é vinculada a um fit por hashes SHA-256. A captura protegida
v3.3.12 deve ter sua própria referência e imagem imediatamente anterior.
A nova projeção compara a referência vinculada à calibração com a imagem
atual por ORB + RANSAC v3.3.11. **Nunca** altera os coeficientes,
não envia cliques e não escreve na memória do jogo.

## 1. Calibração histórica: proveniência desconhecida

O fit antigo `json/calibracao_final_v3_3_5.json` não contém evidência
de que um BMP específico foi obtido **durante o ajuste**. É incorreto
associar automaticamente uma imagem contemporânea à captura recente e
declarar o ajuste antigo válido. Para registrar essa condição, crie
um manifesto de compatibilidade **não verificada**, usando uma imagem
disponível somente como referência não autenticada:

```powershell
python -m aoe2hdcontrol bind-calibration-camera-v3-3-14 `
  --fit json/calibracao_final_v3_3_5.json `
  --reference json/visual_nova_2535_b.bmp `
  --provenance legacy_unverified `
  --note "Imagem antiga nao comprovadamente contemporanea ao ajuste" `
  --output json/vinculo_antigo_v3_3_14.json
```

Isso **não libera projeções para métricas**. Status
`calibration_camera_unverified` é esperado, mesmo que ORB encontre
semelhança.

## 2. Para calibrações novas

Durante o procedimento de nova calibração, preserve BMP da câmera de
origem no próprio momento do ajuste, documentando a origem. Só então
utilize `--provenance contemporaneous_operator_attested` com
`--note` que identifique a sessão e as evidências. Essa proveniência é
**declaração manual**, não prova criptográfica do momento da captura.
Não use esse modo para contornar uma incompatibilidade.

```powershell
python -m aoe2hdcontrol bind-calibration-camera-v3-3-14 `
  --fit json/NOVA_CALIBRACAO.json `
  --reference json/REFERENCIA_DA_CALIBRACAO.bmp `
  --provenance contemporaneous_operator_attested `
  --note "Referencia adquirida durante a sessao de calibracao ..." `
  --output json/vinculo_nova_calibracao.json
```

## 3. Auditar a captura protegida da unidade 2535

```powershell
python -m aoe2hdcontrol project-camera-bound-v3-3-14 `
  --capture json/2535_guard_01.json `
  --fit json/calibracao_final_v3_3_5.json `
  --binding json/vinculo_antigo_v3_3_14.json `
  --calibration-reference json/visual_nova_2535_b.bmp `
  --client-width 1536 --client-height 864 `
  --threshold-px 25 `
  --output json/2535_camera_bound_01.json `
  --overlay json/2535_camera_bound_01.png
```

A imagem PNG mostra o ponto previsto (vermelho), cursor medido (verde)
e linha residual (amarela); é uma **anotação para inspeção**, não
reconhecimento automático do objeto. Mesmo bloqueado, o JSON preserva
o cálculo legado para diagnóstico, mas `eligible_for_numeric_batch=false`.

```powershell
$r=Get-Content .\json\2535_camera_bound_01.json -Raw | ConvertFrom-Json
$r | Select-Object status,reasons,error_px,eligible_for_numeric_batch,
    validated_for_selection | Format-List
Start-Process .\json\2535_camera_bound_01.png
```

Os caminhos de saída nunca sobrescrevem arquivos existentes.

**Limite importante:** a câmera pode mover-se entre snapshots;
a imagem pode não registrar o cursor gráfico; a correspondência entre
Object ID e unidade visual continua pendente. Um vínculo manual e ORB
positivo não demonstram automaticamente que a calibração está correta.
