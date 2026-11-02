# v3.3.1 — validação independente e auditoria geométrica

Compara previsão da projeção afim v3.3 contra pontos **não utilizados no
ajuste**; registra dx/dy, erro euclidiano, RMSE independente, erro máximo,
escalas dos eixos, ângulo entre eixos e determinante. Sinaliza direções
quase paralelas (|cos| > 0,95), transformação quase singular e ajuste com
somente três âncoras. Esses limiares são **heurísticos**, não prova de
que uma projeção isométrica está errada.

Amostras de validação devem representar unidades/edifícios diferentes dos
três de calibração, com mesma câmera, resolução e zoom. O CSV deve usar
ponto decimal e vírgula de separador; colunas obrigatórias:
`world_x,world_y,client_x,client_y`; `object_id` opcional.

## PowerShell

```powershell
cd "C:\Minha_Pasta\Jogos\AoE_II_HD\AoE2HD.control"
git fetch origin
git switch feat/v3-3-1-independent-geometry-audit
python -m unittest discover -s tests -v

# Preencha este CSV com medições REAIS da quarta unidade.
# NÃO use dados sintéticos como evidência.
python -m aoe2hdcontrol audit-projection-v3-3-1 --calibration json/calibracao_v3_3.json --holdouts json/holdouts_v3_3_1.csv --output json/auditoria_v3_3_1.json
Get-Content .\json\auditoria_v3_3_1.json -Raw
```

**Não é seleção programática**, não calcula posição da câmera e não
identifica ponteiro do cursor no mundo. O status é sempre
`audit_only_not_validated`, até validações independentes adicionais.
