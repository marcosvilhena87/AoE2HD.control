# HD Object API Validation v1.4 — Structural Relationship Discovery

## Objetivo
Investigar, **sem escrita no processo**, se os tipos Genie 618/619/620 apresentam referências diretas e persistentes ao Centro da Cidade (109), além da associação espacial identificada pela v1.3. Não se trata de editor de mapas.

## Como usar (PowerShell)
```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git fetch origin main
git reset --hard origin/main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
python -m aoe2hdcontrol objects-v1-4 --pid $gamePid --start-id 2100 --end-id 2300 --samples 3 --interval 2 --pointer-window 0x100 --allow-candidates --output object_validation_v1_4.json
```
**Cuidado:** `reset --hard` descarta alterações rastreadas não salvas. Confirme `git status --short` antes.

Para limitar a leitura a referências, sem posições experimentais, use `--no-positions`. Para investigação inicial, `--pointer-window 0x40` reduz leituras diretas por objeto. O comando aceita no máximo 512 IDs, 20 amostras e janela de 0 a 0x200 bytes, múltipla de 4.

## Conteúdo da evidência
- `snapshots[].objects`: tipo, proprietário, identidade, posições candidatas e distâncias calculadas pela lógica v1.3.
- `snapshots[].candidate_links`: valores de 32 bits dentro de um objeto que coincidem com **endereços** de outros objetos (`direct_object_pointer_candidate`) ou **IDs** (`id_value_coincidence`).
- `link_persistence`: recorrência das mesmas coincidências nas capturas.
- `errors`: falhas de leitura; resultados com erros são incompletos, e o comando retorna código 2.

## Limitações importantes
1. Um ponteiro coincidente é *candidato*, não prova de relação estrutural pai/filho. Coincidência de ID é evidência mais fraca.
2. A janela é limitada ao objeto e não percorre estruturas aninhadas, vtables ou memória arbitrária.
3. Não há garantia de estabilidade de leitura quando o jogo altera a memória entre chamadas; só utilizar partidas locais/offline.
4. `Object+0x3C/0x40` ainda são hipóteses. O reconhecimento dos tipos 618/619/620 permanece **desconhecido**.
5. Capturas de uma mesma partida não equivalem a reprodução entre sessões diferentes.
6. Não promover estados no `AoE2HD.mapping` até existir evidência independente; registrar descobertas novas primeiro ali.

## Interpretação esperada
Verificar se referências são recíprocas ou unidirecionais, se se repetem nos slots 1 e 2 e se persistem em sessões distintas. Se nenhuma referência direta for encontrada, isso **não** refuta associação estrutural indireta. Como controle posterior, observar efeitos da destruição de um Centro da Cidade, sem comandos automatizados.
