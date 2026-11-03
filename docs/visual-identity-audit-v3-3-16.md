# v3.3.16 — Auditoria visual de Object IDs e projeção (offline)

Escopo: **revisão manual**, sem alterar o ajuste v3.3.15 ou liberar seleção.
O objetivo é conservar evidências de correspondência visual entre Object ID,
imagem e ponto de tela previsto/medido; uma imagem estática **não prova**
identidade de objeto sem revisão independente.

## Pré-requisitos

- `AoK HD.exe 5.8.INT`, sessão local PID 4244 já capturada.
- Branch da v3.3.15 disponível; `session_report.json` contendo
  `candidate_session_numeric_passed`, 6 IDs de treino e 10 holdouts.
- Manifesto `json/sessao_v3_3_15.json`, 16 capturas protegidas v3.3.12
  e BMPs originais, sem renomear nem alterar conteúdos.
- Dependências de imagem da suíte anterior (Pillow).

## 1. Preparar as imagens de revisão

A partir de `C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control`:

```powershell
python -m aoe2hdcontrol.visual_identity_audit_v3_3_16 prepare `
  --session-report json/saida_v3_3_15/session_report.json `
  --manifest json/sessao_v3_3_15.json `
  --capture-dir json `
  --fit json/saida_v3_3_15/fit_v3_3_15.json `
  --binding json/saida_v3_3_15/camera_binding_v3_3_15.json `
  --output-dir json/auditoria_visual_v3_3_16
```

O módulo verifica os IDs de holdout, comparação com o manifesto, hashes
de BMPs, conteúdo do JSON de captura, câmera amostrada, PID, identidade
da âncora e consistência das coordenadas dos resultados v3.3.15.
Nenhum coeficiente é recalculado. O destino deve estar vazio.

Saídas: `prepared_report.json`, `reviews.csv` e, para cada holdout
aceito, `<Object ID>_review.png`. Vermelho é posição prevista;
verde é cursor medido; amarelo é diferença. Um erro bloqueado permanece
no relatório e não gera imagem enganosa.

## 2. Revisar manualmente

Abra as dez imagens e compare cada ID com a unidade real usando a
evidência da sessão: tipo, posição e contexto. A anotação sozinha não
identifica a unidade. Edite `reviews.csv` (UTF-8) mantendo:
`object_id,decision,reviewer,reason,overlay_sha256`.

- `confirmed`: operador tem evidência visual independente que justifica
  vincular o ID à unidade indicada.
- `rejected`: correspondência contradita, descreva o motivo.
- `inconclusive`: sem evidência suficiente; **não** substitua por
  confirmação automática. O modelo gera esta decisão como padrão,
  com motivo `not_reviewed`; ela deve ser revisada.
- Em todos os casos, informe `reviewer` e um `reason` detalhado.
  Preserve `overlay_sha256` e não modifique imagens anotadas.

Não descarte rejeições ou pontos com alto erro. Evite alterar posições
ou fazer novas capturas dentro da mesma validação congelada.

## 3. Consolidar as decisões

```powershell
python -m aoe2hdcontrol.visual_identity_audit_v3_3_16 finalize `
  --prepared json/auditoria_visual_v3_3_16/prepared_report.json `
  --reviews json/auditoria_visual_v3_3_16/reviews.csv `
  --output json/auditoria_visual_v3_3_16/final_report.json
```

O relatório final preserva 10 decisões, motivos, erros e hashes; bloqueia
omissões, IDs duplicados e imagens adulteradas. Mesmo quando
`operator_visual_review_complete`, a saída mantém sempre:
`validated_for_selection=false`, `selection_dispatch=not_dispatched`,
`memory_write=false`. Não existe chamada de seleção nesta versão.

## Limites e origem

- A v3.3.15 valida numericamente as dez unidades mas só registra câmera
  `sampled_images_only`; não demonstra estabilidade em todos os quadros.
- A identidade manual pode continuar inconclusiva; screenshot, Object ID
  e posição candidata não são prova criptográfica da unidade.
- A matriz v3 de `AoE2HD.aoe2control` registra OBJ-004 como posição
  candidata e comandos não validados na HD. O `AoE2HD.mapping` mantém
  os status canônicos de memória, sem alteração nesta versão.
- Rodar `python -m unittest tests.test_visual_identity_audit_v3_3_16 -v`
  e `python -m unittest discover -s tests -v`; depois inspecionar
  todas as dez imagens reais. Testes simulados não substituem essa etapa.
