# HD Object API Validation v1.2 — construções e proprietário

**Data:** 2026-10-20. **Escopo:** detecção somente leitura, sem edição de mapas, sem escrita no processo.

## Hipótese experimental

Na sessão observada, `object_id=2188` mostrou `class_id=3`, `genie_type_id=620`, proprietário `0x14BCD01C`, equivalente ao jogador do slot 2. O único edifício informado pelo operador como seu é um Centro da Cidade. Por isso **não** se infere `620=Centro da Cidade`; o tipo `109` é a referência previamente catalogada para TC da Idade das Trevas.

## Comando

```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git fetch origin main
git reset --hard origin/main
python -m unittest discover -s tests -v
$pidJogo = (Get-Process 'AoK HD').Id
python -m aoe2hdcontrol buildings-v1-2 --pid $pidJogo --start-id 2100 --end-id 2300 --allow-candidates
```

**Atenção:** o reset descarta mudanças locais rastreadas; faça backup antes caso existam. IDs devem pertencer à partida atual; use uma faixa que contenha IDs reais conhecidos. A consulta limita o intervalo a 512 IDs e não promete enumeração global. Se desejar ver também jogadores adversários, use `--all-owners`. Filtrar tipo 109: `--type 109`. O ID 2188 é exemplo, não certeza em novas partidas.

## Campos apresentados

- `local_slot`: índice local recuperado da tabela de jogadores neste instante.
- `players_by_pointer`: ponteiros dos jogadores por slot, sempre resolvidos de novo.
- `matches`: construções classe 3 que satisfazem proprietário e tipo opcional. `owner_slot=null` representa ponteiro não reconhecido pela tabela.
- `counters.empty`: entradas vazias na faixa.
- `counters.read_errors`: leituras falhas, que tornam o resultado incompleto; código de saída 2 na CLI.
- `counters.other_owners`, `other_classes`, `other_types`: entradas descartadas por filtro.
- `error_samples`: até 12 falhas individuais. Não interpretar ausência de resultado como ausência de edifícios se houver erros ou se a faixa estiver incompleta.

## Validação

1. Com a partida local ativa, localizar construção do proprietário local.
2. Confrontar ID, tipo e descrição do HUD do Centro da Cidade; o tipo 109 pode variar por estado/era.
3. Confirmar slot do proprietário em duas sessões independentes. Não reutilizar endereço absoluto.
4. Capturar saída JSON e anotar versão do processo, configurações e classe/tipo observados.
5. Registrar evidências no `AoE2HD.mapping` **antes** de atualizar status. Esta implementação não promoveu nenhum campo candidato.

**Limites:** teste unitário com backend simulado não prova resultado em processo real; não se inspecionou a execução deste novo comando em Windows no momento do commit.
