# HD Object API Validation v1.3 — tipos 618, 619 e 620

Implementação experimental de **leitura apenas**. Não edita mapas, não envia ordens e não altera o mapeamento.

## Evidência prévia — v1.2
Em partida local, a consulta 2100–2300 retornou (slot local 1):
- 2180: classe 3, tipo 109, slot 1 (candidato a Centro da Cidade).
- 2181: classe 3, tipo 618, slot 1.
- 2182: classe 3, tipo 619, slot 1.
- 2183: classe 3, tipo 620, slot 1.
- 2188: classe 3, tipo 620, slot 2 (consulta anterior).
Tipos 618/619/620 **continuam desconhecidos**; classe 3 não assegura que sejam edifícios independentes.

## Execução em PowerShell

Atualize apenas com workspace sem modificações que deseje preservar:
```powershell
cd C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control
git status --short
git fetch origin main
git reset --hard origin/main
python -m unittest discover -s tests -v
$gamePid = (Get-Process 'AoK HD').Id
python -m aoe2hdcontrol objects-v1-3 --pid $gamePid --start-id 2100 --end-id 2300 --samples 3 --interval 2 --allow-candidates --output object_validation_v1_3.json
```

Para investigar proximidade geométrica, **em experimento separado** adicionar `--positions`. Esse sinalizador lê `Object+0x3C` / `+0x40` segundo a hipótese de [coordenadas v9.13](https://github.com/marcosvilhena87/AoE2HD.mapping/blob/main/docs/coordenadas_aldeoes_v9_13_2026-10-18.md); não presume eixos, escala nem validade para construções.

## Dados fornecidos
- Por objeto: `object_id`, endereço temporário, classe, Genie Type ID, ponteiro e slot proprietário, se local e posição candidata (opcional).
- `same_owner_ids` e `distances` (quando `--positions`): medidas apenas dentro dos IDs coletados e tipos-alvo, não do mundo inteiro.
- `by_object_id`: amostras temporais para verificar persistência dos campos.
- `errors`: até 25 exemplos de falhas por amostra; se houver erros, CLI retorna código 2.
- Limites: máximo 512 IDs por intervalo, máximo 20 capturas e intervalo 0–30 segundos.

## Interpretação e próximos testes
1. Verificar se os tipos 618/619/620 se repetem para cada dono, inclusive slot 2.
2. Comparar posições candidatas com tipo 109 para testar hipótese de componentes próximos; proximidade **não prova** vínculo estrutural.
3. Repetir em nova sessão e confronto visual (inclusive HUD); IDs e endereços mudam.
4. Preservar classificação desconhecida no catálogo Genie até evidência independente.
5. Qualquer novo mapeamento validado/candidato deve ser primeiro incorporado ao `AoE2HD.mapping` com experimento reprodutível.

Os testes offline não equivalem à execução real no jogo.
