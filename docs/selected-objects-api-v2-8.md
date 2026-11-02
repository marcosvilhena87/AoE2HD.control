# Selected Objects API v2.8 — intenção e verificação (sem despacho)

## Escopo
Esta etapa **não seleciona unidades programaticamente**: produz uma intenção validada
de substituição (1–60 Object IDs únicos) e compara essa intenção com um snapshot
de leitura somente da v2.7. O resultado `observed_match` significa coincidência
observada **sem atribuir causalidade**; `execution` permanece `not_dispatched`.

Não há escrita no jogo, alteração de flags, eventos de mouse, chamadas internas
ou integração Lua. Comandos programáticos HD permanecem **bloqueados** até prova
de mecanismo seguro em partidas locais. O limite 60 é conservador, derivado da
interface móvel observada; não define capacidade de estruturas nem construções.

## Execução
```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
# Selecione antes, manualmente, a unidade com o Object ID mostrado na v2.7.
python -m aoe2hdcontrol selected-v2-8 --pid $gamePid --ids 2607 --allow-candidates --output selected_v2_8.json
Get-Content .\selected_v2_8.json -Raw
```

O ID 2607 é apenas exemplo de uma sessão anterior, não é persistente; substitua
por um ID da sessão atual. Código de saída 0: coincidência estável; 2: sem
coincidência ou snapshot instável; 1: erro. Intenção e observação permanecem
separadas; `completeness=unknown`.

## Referências verificadas
- `AoE2HD.aoe2control/docs/hd-compatibility-matrix-v3.md`: CMD-001 bloqueado.
- `AoE2HD.mapping/docs/evidencia_selecao_v2_6_2026-10-21.md`: contador,
  vetor e flags candidatos; não promover a layout canônico.
- `AoE2HD.control`: leitores e validação v2.7; sem direitos de escrita
  em `WindowsProcessReader`.

## Pendências
Verificação independente do executável por hash, sessões após reinício,
teste real v2.8, instrumentação segura de emissão de comandos e demonstração
de aceitação e execução. Nenhuma delas foi concluída por estes testes simulados.
