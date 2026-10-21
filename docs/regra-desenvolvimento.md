# Regra obrigatória de desenvolvimento entre repositórios

Aplica-se a toda hipótese, experimento, teste exploratório, correção que dependa de comportamento do jogo e implementação de funcionalidade nova no `AoE2HD.control`.

## Consulta prévia obrigatória

Antes de definir solução ou alterar código, consultar o estado atual, na branch pertinente, de **todos os três** repositórios:

1. [AoE2HD.aoe2control](https://github.com/marcosvilhena87/AoE2HD.aoe2control): laboratório de investigação das funcionalidades, contratos, módulos e interface do AoE2Control DE. Usar a HD Compatibility Matrix e as referências primárias para estabelecer o comportamento esperado, **sem presumir compatibilidade binária com HD**.
2. [AoE2HD.mapping](https://github.com/marcosvilhena87/AoE2HD.mapping): **única fonte canônica** de IDs, offsets, endereços, estruturas e estado das evidências. Verificar a versão do jogo, origem, raiz, contexto e situação de validação de cada campo necessário.
3. [AoE2HD.control](https://github.com/marcosvilhena87/AoE2HD.control): implementação e testes atuais, contratos já expostos e regressões a preservar.

Documentar, quando pertinente, os arquivos/revisões consultados e divergências ou ausências encontradas. Se alguma consulta falhar, declarar a limitação e **não tratar dados não verificados como confirmados**.

## Fluxo obrigatório

1. **Formular hipótese ou requisito:** registrar comportamento esperado, versão do jogo, pré-condições e critério observável de sucesso ou refutação.
2. **Cruzar referências:** comparar `AoE2HD.aoe2control` com os catálogos e evidências de `AoE2HD.mapping` antes de escolher identificadores ou endereços.
3. **Preservar incerteza:** distinguir explicitamente hipótese, candidato, observação única, resultado reproduzido experimentalmente e layout definitivamente estabelecido. Repetição em um único cenário não prova estabilidade entre sessões, versões ou classes de objetos.
4. **Atualizar o mapeamento quando necessário:** novas descobertas, revisões ou refutações de memória devem ser documentadas em `AoE2HD.mapping` com evidências positivas e negativas, passos de reprodução, sessão, versão, raiz e status, sincronizando módulos, catálogos e espelhos conforme suas regras. Nunca criar tabela canônica paralela neste repositório.
5. **Implementar no controle:** consumir dados canônicos existentes, isolar experimentos atrás de opções explícitas, limitar operações ao escopo validado e evitar promover offsets candidatos automaticamente.
6. **Validar:** executar testes unitários, integração e regressão aplicáveis; quando envolver leitura real do processo, testar na versão HD correspondente e registrar JSON/CSV ou outra evidência auditável, incluindo casos negativos e mudanças concorrentes.
7. **Concluir somente com rastreabilidade:** documentar o que foi implementado, o que foi observado, o que continua candidato, limitações, resultados dos testes e referências aos três repositórios.

## Limites e responsabilidades

- O repositório `AoE2HD.aoe2control` documenta a referência DE; **não** fornece provas de offsets, ABI, DLLs ou comandos compatíveis com HD.
- O `AoE2HD.mapping` é a fonte de verdade de memória; Object ID de sessão não equivale a Genie Type ID, e endereço absoluto, RVA e offset não são intercambiáveis.
- O `AoE2HD.control` implementa o motor HD; não deve contradizer classificações canônicas nem converter automaticamente resultados plausíveis em fatos.
- Automação de jogo somente em partidas locais/single-player e dentro das regras aplicáveis.
- A regra se aplica ao trabalho realizado durante cada sessão de desenvolvimento, não implica monitoramento automático do GitHub.

## Checklist para mudanças

- [ ] Consultei as revisões atuais dos três repositórios.
- [ ] Identifiquei referência funcional e status de compatibilidade HD.
- [ ] Consultei IDs/offsets no catálogo canônico e preservei o grau de evidência.
- [ ] Registrei no mapeamento qualquer descoberta, revisão ou refutação, se houver.
- [ ] Executei testes aplicáveis e documentei casos positivos e negativos.
- [ ] Registrei limitações, revisões consultadas e resultados reproduzíveis.
