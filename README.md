# 📈 Calculadora de Causal Impact – MVP 

Este repositório contém um MVP de uma calculadora de *Causal Impact*,
pensada para analisar o impacto de campanhas (especialmente de Awareness
e Consideração) em séries temporais, como:

- buscas,
- tráfego orgânico,
- tráfego direto,
- métricas de e-commerce.

A aplicação é feita em **Streamlit** e pode ser executada localmente ou
hospedada no **Streamlit Cloud**.

---

## 🚀 Como usar (visão geral)

1. Faça upload de um arquivo **CSV** contendo:
   - uma coluna `date` em formato `YYYY-MM-DD`;
   - pelo menos uma coluna numérica (target);
   - opcionalmente, colunas numéricas de controle.

2. Escolha:
   - a métrica alvo (target),
   - as séries de controle (se quiser),
   - o período **pré** e **pós** intervenção (campanha/evento).

3. Clique em **“Rodar análise de Causal Impact”**.

A aplicação irá:

- estimar o contrafactual (o que teria acontecido sem a campanha),
- comparar com o observado,
- mostrar o summary numérico,
- mostrar um report em texto,
- e gerar um gráfico Observado vs Contrafactual.

---

## 🧩 Formato do CSV

O CSV deve ter pelo menos:

- `date`: coluna de datas (ex.: `2024-01-01`),
- `target`: métrica que você quer analisar (ex.: `organic_sessions`).

Opcionalmente:

- `control_1`, `control_2`, ...: séries de controle que ajudem o modelo a entender o comportamento da métrica.

Exemplo:

```csv
date,organic_sessions,paid_sessions,search_interest
2024-01-01,1234,567,48
2024-01-02,1300,590,50
2024-01-03,1288,610,51
...
