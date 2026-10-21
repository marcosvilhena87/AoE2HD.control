# AoE2HD.control

Motor de controle experimental para **Age of Empires II HD** (`AoK HD.exe 5.8.INT`, processo x86), inspirado na arquitetura de [AoE2Control](https://aoe2control.github.io/) para Definitive Edition.

## Estado: v0.1 (infraestrutura)

Esta versão **não lê nem escreve memória do jogo**. Implementa uma CLI de diagnóstico, leitura somente dos catálogos canônicos e testes automatizados. Nenhum endereço candidato é promovido a validado.

## Instalação

Requer Python >=3.10. Clone este repositório e `AoE2HD.mapping` na mesma pasta:

```powershell
git clone https://github.com/marcosvilhena87/AoE2HD.control.git
git clone https://github.com/marcosvilhena87/AoE2HD.mapping.git
cd AoE2HD.control
python -m aoe2hdcontrol doctor
python -m aoe2hdcontrol catalog
python -m unittest discover -s tests -v
```

O caminho do catálogo pode ser informado com `--mapping-dir "C:\caminho\AoE2HD.mapping"` ou variável `AOE2HD_MAPPING_DIR`.

## Regra obrigatória para hipóteses e novas implementações

Antes de testar hipóteses, investigar comportamentos ou implementar funcionalidades, **consultar sempre** as versões atuais de [AoE2HD.aoe2control](https://github.com/marcosvilhena87/AoE2HD.aoe2control) (referência funcional DE e matriz de compatibilidade HD) e [AoE2HD.mapping](https://github.com/marcosvilhena87/AoE2HD.mapping) (catálogo canônico e evidências), além do código existente neste repositório. Registrar diferenças, limites de validação, resultados e testes; descobertas de memória devem ser atualizadas primeiro no mapping, sem elevar candidatos a fatos comprovados.

**Procedimento e checklist obrigatórios:** [docs/regra-desenvolvimento.md](docs/regra-desenvolvimento.md).

## Regras

- O [AoE2HD.mapping](https://github.com/marcosvilhena87/AoE2HD.mapping) é a **única fonte de verdade** para IDs e endereços.
- Não existem cópias locais de tabelas de memória.
- Object ID individual é específico da sessão; Genie Type ID representa o tipo.
- Endereço absoluto, RVA e offset não são intercambiáveis.
- Só usar comandos de automação em partidas locais/single-player, respeitando as regras do jogo.
- Nunca assumir que funções, DLLs ou endereços do AoE2Control DE funcionam no HD.

## Próximas fases

1. v0.1: diagnóstico e integração somente leitura com catálogo (este marco).
2. v0.2: localizar processo x86 e validar assinatura da versão, sem leitura arbitrária.
3. v0.3: snapshots observáveis (jogadores, entidades, recursos), a partir de cadeias confirmadas.
4. v0.4: API tipada somente leitura e ciclos de atualização.
5. v0.5: comandos explícitos seguros em partidas locais, após validação experimental.
6. v0.6+: módulos, IPC e renderização.

Referência de produto: https://aoe2control.github.io/. Este projeto é uma implementação independente.
