# v3.3.5 — captura visual com atraso configurável

Captura a leitura experimental de unidade/cursor v3.3.2 e, logo após,
uma **imagem BMP da área cliente** da janela em primeiro plano do
`AoK HD.exe`, usando a API GDI do Windows. O cursor nem sempre aparece
na imagem: sua posição é registrada no JSON para comparação.

**Restrições:** não é uma captura simultânea/atômica; não identifica qual
unidade está sob o cursor; o BMP pode estar preto ou desatualizado no
DirectX/tela cheia. Verifique o conteúdo da imagem. Não habilita
seleção, cliques nem escrita de memória.

## Execução

```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
git fetch origin
git switch feat/v3-3-5-screenshot-delay
git pull --ff-only
python -m unittest discover -s tests -v

$gamePid = (Get-Process 'AoK HD').Id
python -m aoe2hdcontrol capture-anchor-v3-3-5 `
    --pid $gamePid `
    --id 2630 `
    --delay 15 `
    --allow-candidates `
    --output json/2630_visual_v3_3_5.json `
    --image json/2630_visual_v3_3_5.bmp

Get-Content .\json\2630_visual_v3_3_5.json -Raw
Invoke-Item .\json\2630_visual_v3_3_5.bmp
```

Execute o comando completo **uma vez**, alterne para o jogo durante os
15 segundos, posicione o cursor no **centro da base** da unidade, não
mova câmera/unidade, espere a captura. O código não insere seu próprio
cursor na imagem: use `anchor.cursor_after.client` e
`cursor_after_image.client` do JSON ao analisar o BMP.

A imagem é meramente evidência candidata e não valida o Object ID.
Se o jogo estiver em tela cheia exclusiva e o BMP estiver escuro,
é necessária estratégia alternativa de captura, sem concluir
incorretamente que a unidade está ausente.
