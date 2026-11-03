# v3.3.15 — Sessão de calibração com câmera vinculada e holdout independente

Implementação **offline e somente leitura**, para `AoK HD.exe 5.8.INT` (x86).
Não usa novos offsets, não lê o processo, não envia cliques e não prova identidade
visual de Object IDs. Consulte também `docs/regra-desenvolvimento.md`.

## Origem dos contratos

- `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md`: OBJ-004 continua
  candidato; comandos de unidade não são compatíveis automaticamente com HD.
- `AoE2HD.mapping`: fonte canônica; nenhuma promoção de offsets nesta versão.
- `AoE2HD.control`: consome âncoras v3.3.2, detecção ORB/RANSAC v3.3.11
  e binding com SHA-256 v3.3.14.

## Procedimento

1. Em partida local, mantenha câmera e dimensão da janela imóveis. Capture uma
   BMP de referência **durante** a sessão, não depois do ajuste.
2. Capture ao menos **3 âncoras de treinamento** com geometria não degenerada
   e **10 outras unidades** para holdout, com Object IDs distintos e mesmo PID.
   As âncoras devem seguir o esquema `hd-synchronized-anchor-v3.3.2`.
3. Para cada observação, salve BMP contemporâneo e SHA-256 correspondente.
   Registre manualmente sessão e nota de proveniência. Uma afirmação manual não
   substitui medição atômica da câmera.
4. Monte um manifesto JSON. Caminhos relativos são resolvidos em relação ao
   diretório do manifesto:

```json
{
  "schema": "hd-camera-session-v3.3.15",
  "session": "teste-local-01",
  "note": "BMPs capturados durante a mesma sessao sem deslocar a camera",
  "reference_image": "camera_ref.bmp",
  "reference_sha256": "COLOQUE_SHA256_REAL_AQUI",
  "anchors": [
    {
      "role": "train",
      "anchor": {"schema": "hd-synchronized-anchor-v3.3.2"},
      "camera_image": "camera_ancora_01.bmp",
      "camera_sha256": "COLOQUE_SHA256_REAL_AQUI"
    }
  ]
}
```

O registro de âncora abreviado é apenas ilustrativo: inclua todos os campos
de uma captura real v3.3.2 e repita os registros até o mínimo requerido.
Os papéis `train` e `holdout` são explícitos e não se sobrepõem.

Execute:

```powershell
python -m aoe2hdcontrol.calibration_session_v3_3_15 `
  --manifest json/sessao_v3_3_15.json `
  --output-dir json/saida_v3_3_15 `
  --threshold-px 25 --min-holdouts 10
```

Se aprovado **apenas numericamente**, a saída contém
`session_report.json`, `fit_v3_3_15.json` e
`camera_binding_v3_3_15.json`. Se bloqueado, apenas o relatório é salvo,
com razões e checks por âncora. Diretório não vazio não é sobrescrito.

## Critérios e limitações

- SHA-256 de cada BMP; dimensões idênticas; detecção de câmera estática entre
  imagem de referência e imagem da amostra; PID único e IDs únicos.
- Mínimo 10 holdouts fora do treino; erro RMSE máximo 25 px e filtros
  geométricos da v3.3.2.
- `candidate_session_numeric_passed` **não significa seleção validada**.
- A estabilidade é amostrada; o motor não garante que a câmera não se moveu
  entre quadros, nem que cada BMP e âncora sejam simultâneos.
- A posição de cursor atribuída à unidade segue interpretação manual; a
  identidade visual entre Object ID e unidade permanece sem prova.
- Sem testemunho criptográfico de relógio/captura; manifesto e nota são
  evidência declarada, não atestação automática.
- Seleção: `validated_for_selection=false`, `selection_dispatch=not_dispatched`,
  `memory_write=false`.

Validação automatizada proposta:
`python -m unittest tests.test_calibration_session_v3_3_15 -v`.
É obrigatório executar com evidências reais do jogo antes de qualquer
conclusão operacional.
