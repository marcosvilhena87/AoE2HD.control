# Experimento v3.3.16 — unidade isolada: A/B/C

**Objetivo:** buscar evidência de correspondência entre um Object ID lido na
memória e uma unidade visual que o operador acompanha. Evitar repetir o caso
2535: a imagem com cursor (1003,552) num aglomerado **não identifica** a
unidade 2535.

A auditoria da v3.3.16 é *offline* e exige três capturas v3.3.12 e três
revisões explícitas v3.3.15, em uma única partida e câmera de referência.

- **A (original):** isole visualmente uma única unidade por ações manuais,
  registre uma captura protegida e anote seu Object ID por evidência
  independente. A seleção manual sozinha não estabelece Object ID.
- **B (movida):** mova **manualmente** essa unidade para uma posição
  distinta do mapa (por padrão pelo menos 1,0 unidade mundial), sem mover a
  câmera; registre a mesma identidade e capture seu novo ponto de base.
- **C (retorno):** ordene manualmente o retorno à posição inicial; registre
  novamente ao parar (padrão até 0,10 unidade mundial de A e até 20 px do
  cursor inicial). Não confunda movimento da unidade e deslocamento de câmera.

## 1. Três capturas

Com o jogo em primeiro plano, mantenha a mesma referência BMP (criada em
v3.3.12) e o mesmo PID, sem clicar automaticamente:

```powershell
$gamePid=(Get-Process 'AoK HD').Id
python -m aoe2hdcontrol capture-camera-guarded-v3-3-12 `
  --pid $gamePid --id 2535 --delay 20 --allow-candidates `
  --reference json/camera_ref_sessao_01.bmp `
  --image-before json/2535_exp_A_pre.bmp `
  --image-after json/2535_exp_A_post.bmp `
  --output json/2535_exp_A.json
```

Faça a movimentação manual e repita com os arquivos **B** e, depois
do retorno, **C**. Use um Object ID comprovadamente correto; não é
obrigatório que seja 2535. Não reutilize arquivos existentes. Mantenha
o cursor imóvel durante cada amostragem.

## 2. Preparar imagens de revisão

```powershell
foreach ($fase in @("A","B","C")) {
  python -m aoe2hdcontrol prepare-identity-v3-3-15 `
    --capture "json/2535_exp_$fase.json" `
    --overlay "json/2535_exp_$fase.review.png" `
    --output "json/2535_exp_$fase.pending.json"
  Start-Process "json/2535_exp_$fase.review.png"
}
```

Inspecione cada imagem: unidade isolada, cursor em sua base, identidade do
Object ID sustentada por evidência adicional. Se houver dúvida use
`--identity uncertain`; a auditoria bloqueará o experimento.

## 3. Declaração manual por fase

Somente após comprovar de forma independente a identidade:

```powershell
foreach ($fase in @("A","B","C")) {
  python -m aoe2hdcontrol review-identity-v3-3-15 `
    --input "json/2535_exp_$fase.pending.json" `
    --identity confirmed --isolated --cursor-on-target `
    --reviewer "operador" `
    --note "Identificacao independente documentada; mesma unidade isolada na fase $fase" `
    --output "json/2535_exp_$fase.reviewed.json"
}
```

Esses comandos **não comprovam a identidade por si**; conservam apenas
a declaração do operador. Escreva na nota qual evidência independente foi
realmente usada. Não declare confirmação se depender exclusivamente do
palpite sobre o sprite ou da posição projetada.

## 4. Auditoria A/B/C

```powershell
python -m aoe2hdcontrol audit-controlled-transition-v3-3-16 `
  --a json/2535_exp_A.reviewed.json `
  --b json/2535_exp_B.reviewed.json `
  --c json/2535_exp_C.reviewed.json `
  --min-world-move 1.0 `
  --max-world-return 0.10 `
  --min-cursor-move 15 `
  --max-cursor-return 20 `
  --output json/2535_exp_ABC_audit.json
```

A validação rejeita hash divergente de captura, BMP ou câmera de referência;
PID/ID diferentes; fase não confirmada; câmera diferente entre quaisquer
pares; ausência de movimento e falha do retorno; cursor em posição
incompatível; ou reutilização das mesmas capturas. São comparadas as imagens
com ORB + RANSAC v3.3.11.

Status positivo: `candidate_manual_transition_correlated`, sem liberação
para recalibração ou seleção. Status negativo:
`transition_blocked`, com motivos no campo `reasons`.

**Limite:** essas evidências não demonstram automaticamente que o sprite
seguido pelo operador é de fato o Object ID registrado. Mesmo a sequência
A/B/C precisa de evidência externa de identidade e inspeção humana.
