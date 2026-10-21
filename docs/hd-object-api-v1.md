# HD Object API v1 — experimental (somente leitura)

Data: 2026-10-20. Referência: [HD Compatibility Matrix v1](https://github.com/marcosvilhena87/AoE2HD.aoe2control/blob/main/docs/hd-compatibility-matrix-v1.md).

## O que foi implementado

- `WindowsProcessReader(pid)`: conecta a um PID explícito e localiza o módulo `AoK HD.exe`; solicita somente `PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION`. Não injeta DLLs nem faz escrita.
- `MappingOffsets`: carrega o catálogo canônico `dados/catalogos/estruturas_memoria.csv` através de `catalog.load_catalog("memory",...)`, sem copiar tabelas.
- `HDObjectAPI.get_assigned_player()`: segue cadeia historicamente registrada de Owner, World, índice local e tabela de jogadores.
- `HDObjectAPI.get_object_by_id(id)`: consulta tabela `World+0x0E8`, verifica `Object+0x08`, tenta recuperar classe e Genie Type ID, e registra proprietário candidato.
- `get_objects_by_ids(ids)` e `get_objects_by_class(class_id, ids)`: filtros sobre **lista explícita de IDs**. Ainda não há busca global integral, pois limite/tamanho da coleção não foi validado.
- `HDObject` e `HDPlayer`: dataclasses imutáveis com os dados encontrados e indicação dos campos candidatos.
- `python -m aoe2hdcontrol object --pid ... --id ... --allow-candidates`: consulta por um ID conhecido da sessão.

## Exemplo no PowerShell

```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
python -m unittest discover -s tests -v
Get-Process "AoK HD" | Select-Object Id,ProcessName
python -m aoe2hdcontrol --mapping-dir "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.mapping" object --pid 1234 --id 2188 --allow-candidates
```

**Substitua `1234` pelo PID obtido e `2188` pelo ID individual observado na partida atual.** IDs mudam entre sessões. O caminho do mapping pode ser omitido quando os dois repositórios são irmãos.

## Regras de segurança de evidências

- `Object+0x08`, `Object+0x0C`, `Object+0x10` estão marcados como `hipotese`: o comando exige `--allow-candidates`. O opt-in não promove validação.
- Classe: `Object+0x078`, `Object78Target+0x00C` e tipo: `ObjectTypeTarget+0x10` possuem status `validado` no mapping.
- Não usa `Object+0x3C/+0x40` para posicionamento, pois esses candidatos ainda não existem como endereços estruturados validados no catálogo canônico. O retorno `position=None` é intencional.
- Nenhum comando de movimentação, escrita ou escaneamento amplo do espaço de endereços foi adicionado.
- A versão `AoK HD.exe 5.8.INT` deve ser confirmada pelo operador: o leitor só valida o nome do módulo, não o hash nem assinatura do binário.
- O alvo deve ser uma partida local/offline. Ponteiros inválidos, mudanças de sessão e leituras não atômicas podem causar erros — não reutilize ponteiros, IDs ou memória de sessões antigas.

## Testes

`tests/test_object_api.py` exercita bloqueio de candidatos, jogador local, ID, classe, tipo, proprietário, filtros, ausência e inconsistência de ID com memória simulada. **Os testes de leitura real em Windows não foram executados neste ambiente.**

## Critérios ainda pendentes para marcar HD Object API v1 como validada em jogo

1. Validar assinatura/versão do executável, bitness e permissão de leitura de processo de forma independente.
2. Confirmar no HD em duas sessões IDs, proprietários e campos candidatos usados pela API.
3. Descobrir limites da tabela global de objetos e política de ID reciclado sem varredura arbitrária.
4. Completar as coordenadas mediante evidência canônica e validar unidades de várias classes.
5. Criar teste real de captura e comparação com HUD e seleção do jogador.
6. Registrar **qualquer descoberta de memória primeiro** no AoE2HD.mapping.

Esta versão é uma implementação inicial **experimental**, não equivalência certificada com APIs nativas do AoE2Control DE.
