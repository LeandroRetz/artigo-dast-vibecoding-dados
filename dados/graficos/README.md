# Figuras e tabelas

Gerado por `06-graficos.py` a partir de `out/_tab_detalhado.csv`,
`out/_tab_resumo.csv` e os logs das oito varreduras.

```bash
python3 -m venv .venv && .venv/bin/pip install matplotlib pandas
.venv/bin/python 06-graficos.py
```

Cada PNG vem acompanhado do CSV que o originou, para conferência e para
reconstruir a figura em outra ferramenta.

| arquivo | conteúdo | destino sugerido |
|---|---|---|
| `fig1-severidade-por-modelo.png` | achados únicos por severidade | Seção 4.2 — H1 |
| `fig2-achados-por-endpoint.png` | métrica normalizada, por perfil | Seção 4.2 — H2 |
| `fig3-high-por-classe.png` | severidade alta, por classe | Seção 4.4 |
| `fig4-owasp.png` | distribuição OWASP Top 10 | Seção 4.3 — H3 |
| `fig5-sobreposicao-perfis.png` | achados exclusivos de cada perfil | Seção 4.2 |
| `tab1-resumo.png` | resumo consolidado | Seção 4.2 |
| `tab2-high-por-classe.png` | severidade alta com CWE | Seção 4.4 |
| `tab3-cobertura.png` | verificação das oito varreduras | Seção 3.3.1 |

## Duas contagens diferentes, ambas corretas

- **Achado único** — deduplicado por `(endpoint, parâmetro, regra)`. É o que
  todas as figuras usam.
- **Instância bruta** — cada ocorrência no relatório do ZAP. Um mesmo achado
  pode ter várias. Aparece em `out/_tab_resumo.csv` na coluna
  `instancias_brutas`.

A razão "por endpoint" também aparece em duas formas: a `fig2` calcula dentro
de cada perfil (é a coluna do agregador); a `tab1` consolida os dois perfis
antes de dividir. Os números diferem por construção.

## Escolhas de codificação visual

Severidade é escala **ordenada**, então usa uma rampa sequencial de um único
hue (azul, claro→escuro), não cores categóricas. Perfis e classes de
vulnerabilidade são **identidades**, e usam a ordem fixa de slots categóricos.
Em `fig5`, "nos dois perfis" recebe um cinza neutro por não ser uma terceira
categoria, e sim a interseção.

Todas as paletas foram verificadas com o validador do design system
(banda de luminosidade, piso de croma, separação sob daltonismo, contraste
contra a superfície). Onde o contraste ficou abaixo de 3:1, os valores vão
rotulados diretamente sobre as barras — a magnitude nunca depende só da cor.

## Cautelas ao usar estes números

As regras de injeção SQL rodaram com `threshold: low`, elevando
deliberadamente a sensibilidade e, com ela, a taxa de falso positivo nessa
classe. A comparação entre modelos na severidade alta precisa declarar isso.

A contagem bruta de URLs descobertas (`tab3`) mede esforço de exploração, não
superfície de ataque: o fallback das SPA responde 200 a qualquer caminho.
Use a métrica normalizada por endpoint.

27 achados ficaram sem categoria OWASP automática
(`out/_pendente_mapeamento.csv`) e não entram na `fig4`.
