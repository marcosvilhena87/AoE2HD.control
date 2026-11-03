# v3.3.18 — Auditoria de repetibilidade dinâmica em múltiplas sessões

## Escopo

Auditoria **offline e somente leitura** dos resultados da v3.3.17.
Agrega experimentos com alvo móvel e controle negativo, diferentes
direções e reinícios declarados pelo operador. Mantém toda rejeição;
não reduz o erro eliminando observações desfavoráveis.

Fontes verificadas: `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md`
(OBJ-004 permanece candidato, CMD-001 bloqueado);
`AoE2HD.mapping/docs/criterios.md` (IDs/endereço de sessão não são
mapeamento canônico); `AoE2HD.control` v3.3.15 e v3.3.17.

## Critérios experimentais (padrão)

- **Três sessões** independentes, com PIDs diferentes, `boot_id` exclusivo,
  declaração de reinício e identificação da versão do jogo.
- **Duas experiências por sessão** (mínimo seis), IDs de objeto não
  reutilizados **dentro** da mesma sessão e controles negativos por ensaio.
- **Quatro quadrantes** cobertos ao longo das experiências:
  ES, EN, WS e WN (delta de tela). Movimento sobre um eixo não conta
  como cobertura de quadrante.
- Cada sessão precisa de **calibração v3.3.15 própria**, com 6 âncoras de
  treino e 10 holdouts aprovados **no mesmo PID**, e arquivo de fit cuja
  integridade corresponda ao relatório de calibração.
- Cada ensaio precisa de relatório e manifesto v3.3.17 íntegros, com
  quatro capturas originais ainda acessíveis, vinculadas por SHA-256.
- Mesmo SHA-256 do executável entre sessões e versão declarada igual.
- Limiares de verificação: movimento do alvo ≥30 px e ≥0,25 unidade
  mundial; controle ≤8 px e ≤0,2 unidade mundial; erro individual ≤12 px,
  além do RMSE conjunto ≤12 px.
- O programa **não comprova** reinícios pela mudança de PID ou por
  `boot_id`. Esses elementos são atestados pelo operador, não
  autenticados pelo SO.

**Atenção:** reutilizar a calibração v3.3.15 de uma sessão anterior
com um PID novo deve reprovar a auditoria. Uma câmera/zoom/configuração
diferente também exige capturas e calibração novas.

## Organização sugerida dos arquivos

```text
json/
  multissessao_v3_3_18/
    sessao_01/
      calibracao/session_report.json
      calibracao/fit_v3_3_15.json
      experimento_01/dynamic_manifest_v3_3_17.json
      experimento_01/dynamic_report.json
      experimento_02/dynamic_manifest_v3_3_17.json
      experimento_02/dynamic_report.json
    sessao_02/...
    sessao_03/...
    manifest_v3_3_18.json
```

Os BMPs e arquivos JSON de captura originais devem continuar disponíveis
nos caminhos apontados pelos relatórios v3.3.17. Não altere seus conteúdos.

## Manifesto agregador

`manifest_v3_3_18.json`, com caminhos **relativos à localização do
próprio manifesto** (caminhos absolutos também são aceitos):

```json
{
  "schema": "hd-multisession-dynamic-v3.3.18",
  "operator_note": "Três execuções distintas, movimentos manuais, controles imóveis",
  "sessions": [
    {
      "session_id": "sessao-01",
      "boot_id": "reinicio-declarado-01",
      "pid": 4244,
      "restart_attestation": "O operador confirmou a nova inicialização do executável",
      "game_version": "5.8.INT",
      "executable": {"path": "C:/CAMINHO/AoK HD.exe", "sha256": "<sha256_real>"},
      "calibration_report": {"path": "sessao_01/calibracao/session_report.json", "sha256": "<sha256_real>"},
      "fit_file": {"path": "sessao_01/calibracao/fit_v3_3_15.json", "sha256": "<sha256_real>"},
      "trials": [
        {
          "manifest": {"path": "sessao_01/experimento_01/dynamic_manifest_v3_3_17.json", "sha256": "<sha256_real>"},
          "report": {"path": "sessao_01/experimento_01/dynamic_report.json", "sha256": "<sha256_real>"}
        },
        {
          "manifest": {"path": "sessao_01/experimento_02/dynamic_manifest_v3_3_17.json", "sha256": "<sha256_real>"},
          "report": {"path": "sessao_01/experimento_02/dynamic_report.json", "sha256": "<sha256_real>"}
        }
      ]
    }
  ]
}
```

Adicione `sessao-02` e `sessao-03` com os próprios resultados
de calibração, PID, relatórios e experiências. **Não invente hashes ou
declare reinícios não realizados.** PIDs podem ser reutilizados pelo
Windows; o rótulo e a declaração de reinício são apenas evidência
de operador e não comprovação automática.

Para criar uma entrada com hash correto no PowerShell:

```powershell
function Evidencia([string]$caminho) {
    if (-not (Test-Path -LiteralPath $caminho -PathType Leaf)) {
        throw "Arquivo ausente: $caminho"
    }
    @{
        path = (Resolve-Path -LiteralPath $caminho).Path
        sha256 = (Get-FileHash -LiteralPath $caminho -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
# Exemplo:
Evidencia "json/saida_v3_3_15/session_report.json"
```

Para obter o caminho do executável do processo real:

```powershell
(Get-Process 'AoK HD').Path
```

Se o caminho estiver ausente, localize-o manualmente e confira o
SHA-256 antes de criar o manifesto.

## Executar a auditoria

Depois de completar as **seis** experiências e as **três**
calibrações, execute:

```powershell
python -m aoe2hdcontrol.multisession_identity_v3_3_18 `
  --manifest json/multissessao_v3_3_18/manifest_v3_3_18.json `
  --output-dir json/resultado_multissessao_v3_3_18
```

Saída: `multisession_report.json`, contendo todos os motivos de
bloqueio, ensaios, quadrantes e RMSE conjunto. Diretório de destino
deve estar vazio. O status `candidate_multisession_repeatability_passed`
significa apenas que os critérios de repetibilidade **experimental**
foram atendidos, nunca que a identificação visual foi comprovada.

Reexecutar em novo diretório; não sobrescrever relatórios anteriores.

## Limitações e segurança

- A análise é de relatórios já produzidos, não executa captura,
  não envia clique ou comando e não escreve memória do jogo.
- A integridade é de arquivos e hashes declarados, não uma cadeia
  de custódia inviolável. Evidência manipulada com hashes atualizados
  pode escapar aos controles, exigindo auditoria independente.
- Não prova movimento continuamente observado, nem captura atômica.
- O fit e as coordenadas do jogo permanecem **candidatos**; OBJ-004
  não é automaticamente promovido no mapping.
- Sem seleção automática, sempre:
  `validated_for_selection=false`,
  `selection_dispatch=not_dispatched`, `memory_write=false`.

Testes:
```powershell
python -m unittest tests.test_multisession_identity_v3_3_18 -v
python -m unittest discover -s tests -v
```
