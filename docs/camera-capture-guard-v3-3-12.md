# v3.3.12 — Controle de estabilidade da câmera durante a captura

Nova coleta **somente leitura**, sem clique ou recalibração. A antiga v3.3.5
permanece disponível. Esta versão adiciona uma referência de câmera e três
comparações ORB + RANSAC por unidade: referência → antes, referência → depois
e antes → depois. Qualquer evidência de movimento, ambiguidade, falha no
screenshot ou inconsistência de cursor causa `capture_blocked`. As evidências
são preservadas para auditoria, inclusive se a captura for bloqueada.

## Dependências

```powershell
python -m pip install opencv-python numpy Pillow
```

## 1. Registrar uma imagem de referência

Com o jogo em primeiro plano e câmera posicionada no enquadramento desejado:

```powershell
$gamePid=(Get-Process 'AoK HD').Id
python -m aoe2hdcontrol camera-reference-v3-3-12 `
  --pid $gamePid `
  --image json/camera_ref_sessao_01.bmp
```

**A referência não deve ser capturada novamente após deslocamentos da câmera
sem documentar o início de uma nova sessão.** O arquivo pré-existente não é
sobrescrito. Revise visualmente se o BMP contém imagem atual e não tela preta
ou quadro stale devido ao GDI.

## 2. Capturar unidade com proteção

```powershell
python -m aoe2hdcontrol capture-camera-guarded-v3-3-12 `
  --pid $gamePid `
  --id 2535 `
  --delay 20 `
  --allow-candidates `
  --reference json/camera_ref_sessao_01.bmp `
  --image-before json/2535_guard_pre_01.bmp `
  --image-after json/2535_guard_post_01.bmp `
  --output json/2535_guard_01.json
```

O programa aguarda o prazo, captura a imagem antes da leitura de Object ID,
registra coordenadas sincronizadas do cursor e da unidade, tira a imagem depois
e compara todas as capturas. Retorno: 0 para
`candidate_capture_accepted`, 2 para `capture_blocked` e 1 para erro
operacional. Caminhos de saída existentes ou repetidos são recusados, evitando
sobrescrever dados anteriores. Em condições normais, um bloqueio gera JSON;
falha de pré-validação (ex.: referência ausente) impede a captura.

## 3. Inspecionar os resultados

```powershell
$r=Get-Content .\json\2535_guard_01.json -Raw | ConvertFrom-Json
$r | Select-Object status,object_id,camera_consistency,
   cursor_stable,anchor_usable,validated_for_selection | Format-List
$r.camera_checks.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{
        Comparison=$_.Name
        Status=$_.Value.status
        DX=$_.Value.dx_px
        DY=$_.Value.dy_px
        Inliers=$_.Value.inliers
    }
} | Format-Table -AutoSize
```

**Limites:** as imagens são adquiridas sequencialmente; movimentos da
câmera entre snapshots podem passar despercebidos. ORB encontra padrões
visuais, não prova a identidade da unidade. Um estado
`candidate_capture_accepted` **não** é autorização para selecionar unidades,
nem substitui a conferência visual ou valida automaticamente o lote da v3.3.7.
O programa ainda não corrige offsets de projeção. Para comparar movimento
de câmera em sessões longas, mantenha a mesma referência e verifique todas
as capturas individualmente.
