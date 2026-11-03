# Ciclo de unidades v2.9 — contrato preparatório, sem escrita

## Objetivo

Separar **identificar por Object ID → observar seleção → solicitar movimento → verificar evidência posterior** sem fingir que o Age of Empires II HD já dispõe de um despachante de comandos validado.

A API pública fica em `aoe2hdcontrol.unit_cycle_v2_9`:

- `make_move_request(ids, (x, y), session=...)` valida um pedido imutável; IDs são **da sessão**, não Genie Type IDs.
- `identify(api, request)` localiza IDs explicitamente informados e exige que o ponteiro candidato de dono coincida com o jogador local. Falha com dúvidas; não enumera objetos globais.
- `observe_selection(api, request)` compara com o snapshot experimental v2.7, **não seleciona nenhuma unidade**.
- `dispatch_move(request, transport=..., offline_confirmed=True, selection=...)` estabelece a fronteira de envio; sem backend externo explícito, `DisabledTransport` recusa. Apenas partidas locais/offline.
- `verify_observed_movement(..., before, after)` aceita *evidências externas* de posição por Object ID e mede chegada ao destino. **Não** considera isso prova de causalidade ou confirmação de execução.

## Exemplo apenas com transporte simulado

```python
from aoe2hdcontrol.unit_cycle_v2_9 import make_move_request, dispatch_move

request = make_move_request([2183], (30, 40), session="sessao-local-1")
# Exige snapshot de seleção obtido de observe_selection(api, request);
# o backend padrão SEMPRE recusará, mesmo se o snapshot coincidir.
```

Nenhuma função desta versão escreve no processo, injeta DLL, emula mouse/teclado, envia comandos Lua, usa endereços hardcoded ou inventa posição. Os testes com transportes falsos provam apenas o fluxo lógico. O `HDObjectAPI.get_object_by_id` atualmente devolve `position=None`; coordenadas observadas de fato precisam ser validadas no mapping antes de qualquer integração real.

## Evidência e rastreabilidade

- **HD target:** `AoK HD.exe 5.8.INT`, PE32/x86; hash da build não atestado nesta mudança.
- **Referência funcional:** `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md`, CMD-001 bloqueado, OBJ-004 posição pendente, OBJ-005 seleção experimental delimitada.
- **Fonte canônica:** `AoE2HD.mapping/README.md`, `dados/enderecos.csv` e evidência experimental de seleção v2.6. Nenhum offset novo foi descoberto ou promovido; portanto não houve mudança de catálogo.
- **Implementação existente:** `selected_objects_v2_7.py` e `selected_objects_v2_8.py`, snapshots não atômicos, candidatos e `completeness=unknown`.

## Gates antes de habilitar despacho real

1. Verificar hash SHA-256 da build e repetir ensaios após reiniciar jogo e processo.
2. Comprovar identidade, dono, validade temporal de IDs e substituição de objetos durante leitura.
3. Validar posições X/Y no mapping mediante trajetórias e unidades múltiplas, incluindo casos negativos.
4. Identificar um mecanismo de despacho legítimo e testado **para HD**, sem importar ABI da Definitive Edition.
5. Somente então criar transporte real, com opt-in offline/local, checagem de sessão e observação antes/depois. ACK de transporte não prova execução.
6. Integrar Lua apenas após comprovação de mecanismo de comunicação/controle, com testes end-to-end auditáveis no Windows.

## Testes

```powershell
python -m unittest tests.test_unit_cycle_v2_9 -v
python -m unittest discover -s tests -v
```

Esses testes não substituem validação no jogo. Não há reivindicação de comando programático, seleção por código Lua ou movimento real nesta versão.
