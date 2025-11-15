# 📈 Causal Impact – MVP 

Este é um MVP de uma calculadora de *Causal Impact* feita para testar,
de forma simples, o impacto real de campanhas de Awareness e Consideração usando séries temporais (CSV).

O objetivo do MVP é permitir que qualquer pessoa da equipe consiga:

- Fazer **upload de um CSV** com série temporal
- Selecionar **target** e **covariáveis**
- Definir **período pré** e **pós-intervenção**
- Rodar o **modelo Causal Impact**
- Visualizar:
  - Gráfico *observado vs. contrafactual*
  - Impacto total e percentual
  - Intervalo de confiança
  - Sumário automático

O deploy está feito via **Streamlit Cloud**, permitindo que qualquer pessoa teste o MVP diretamente pela interface web.

---

## 🚀 Como rodar localmente (opcional)

Criar ambiente virtual (opcional):

```bash
python -m venv .venv
source .venv/bin/activate    # macOS/Linux
# ou
.venv\Scripts\Activate.ps1   # Windows
