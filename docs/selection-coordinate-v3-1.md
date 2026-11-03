# v3.1 — seleção experimental assistida por coordenadas

A v3.1 **envia um único clique esquerdo pelo Windows** após autorização
explícita. A coordenada física de tela `--x/--y` deve ser fornecida pelo
operador: **não existe mapeamento Object ID → posição na tela**.
`--id` é apenas o resultado esperado, verificado pela API v2.7.
Não escreve na memória e não usa funções internas do AoK HD.exe.

Proteções: exige `--allow-candidates --arm`, PID explícito, snapshot inicial
estável, janela do PID em primeiro plano e coordenada dentro da área cliente.
Sem repetição, sem selecionar grupos, sem automatizar qualquer ordem militar.
Um clique pode acertar UI/terreno se as coordenadas estiverem erradas.

## Experimento local, somente single-player/offline

1. Abra o jogo em janela ou modo com resolução fixa. Selecione a unidade-alvo
   manualmente para descobrir seu Object ID usando `selected-v2-7`.
2. Anote uma coordenada de **tela** sobre a unidade; verifique que não cobre
   menus. Selecione outra unidade antes do teste.
3. Execute no PowerShell (substitua ID, X, Y pelas observações reais):

```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
git fetch origin
git switch feat/v3-1-coordinate-assisted-selection
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
python -m aoe2hdcontrol select-screen-v3-1 --pid $gamePid --id 2630 --x 500 --y 400 --allow-candidates --arm --output selection_v3_1.json
Get-Content .\selection_v3_1.json -Raw
```

4. Ao aparecer a instrução, volte à janela do jogo dentro de **cinco
segundos**. O processo deve estar em primeiro plano no instante do clique.
Os valores 2630/500/400 acima são apenas ilustrativos; não execute sem
substituir e verificar.

Estados: `observed_match` ou `target_not_observed`, se o clique foi
emitido. Falhas de foco ou coordenada produzem erro sem despachar.
`dispatch=windows_mouse_click_attempted` significa tentativa de emissão
pelo sistema operacional, **não prova aceitação pelo jogo**. A confirmação
é pelo snapshot; a causalidade permanece `not_proven`.

## Referências
- AoE2HD.aoe2control: matriz HD v3, despacho nativo não validado.
- AoE2HD.mapping: evidência de seleção v2.6, offsets experimentais.
- AoE2HD.control: verificações v2.7-v3.0 e bloqueio de seleção nativa v2.9.

**Limitações:** testes simulados não validam o SendInput no Windows; DPI,
janelas sobrepostas, movimento da unidade, menus e tempo entre clique e
leitura podem interferir. O gate de despacho nativo v2.9 permanece bloqueado.
