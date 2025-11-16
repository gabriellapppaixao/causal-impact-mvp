import io
from datetime import datetime, date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from causalimpact import CausalImpact  # vem do pacote tfcausalimpact


# -----------------------------
# Helpers
# -----------------------------
def load_csv(uploaded_file: io.BytesIO) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)

    # Normalizar nome da coluna de data
    possible_date_cols = ["date", "data", "dia", "Date", "DATA"]
    date_col = None
    for c in df.columns:
        if c in possible_date_cols:
            date_col = c
            break

    if date_col is None:
        # Tenta primeira coluna como data
        date_col = df.columns[0]

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(by=date_col)
    df = df.reset_index(drop=True)
    df = df.rename(columns={date_col: "date"})
    return df


def build_pre_post_periods(df: pd.DataFrame, intervention_date: date):
    """Retorna períodos no formato aceito pelo CausalImpact (strings de data)."""
    if df.empty:
        raise ValueError("O CSV está vazio.")

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    if not (min_date <= intervention_date <= max_date):
        raise ValueError(
            f"A data de intervenção ({intervention_date}) precisa estar "
            f"dentro do intervalo de datas do CSV ({min_date} a {max_date})."
        )

    # Pré = tudo até o dia anterior à intervenção
    pre_end = intervention_date.fromordinal(intervention_date.toordinal() - 1)
    if pre_end < min_date:
        raise ValueError(
            "Período pré-intervenção ficou vazio. "
            "Escolha uma data de intervenção mais para frente."
        )

    pre_period = [str(min_date), str(pre_end)]
    post_period = [str(intervention_date), str(max_date)]
    return pre_period, post_period


# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="Causal Impact MVP", layout="wide")

st.title("🔍 MVP – Calculadora de Causal Impact")
st.write(
    """
    Faça upload de um CSV com **datas** e **uma métrica** (por exemplo, `organic_sessions`)  
    e escolha a data em que a campanha começou.  
    O app estima qual teria sido o comportamento **sem campanha** e compara com o observado.
    """
)

uploaded_file = st.file_uploader("Envie um CSV", type=["csv"])

if uploaded_file is None:
    st.info("Envie um CSV para começar.")
    st.stop()

# -----------------------------
# Dados
# -----------------------------
try:
    df = load_csv(uploaded_file)
except Exception as e:
    st.error(f"Erro ao ler o CSV: {e}")
    st.stop()

metric_cols = [c for c in df.columns if c != "date"]

if not metric_cols:
    st.error("Não encontrei nenhuma coluna de métrica além da coluna de data.")
    st.stop()

st.subheader("Pré-visualização dos dados")
st.dataframe(df.head())

min_date = df["date"].min().date()
max_date = df["date"].max().date()
st.write(f"Intervalo de datas no CSV: **{min_date}** até **{max_date}**")

metric = st.selectbox("Escolha a métrica para analisar", metric_cols)

default_intervention = min_date.fromordinal(min_date.toordinal() + 40)  # só um chute
if default_intervention > max_date:
    default_intervention = min_date

intervention_date = st.date_input(
    "Data de início da campanha (intervenção)",
    value=default_intervention,
    min_value=min_date,
    max_value=max_date,
)

if st.button("Rodar análise de Causal Impact"):
    with st.spinner("Rodando modelo de Causal Impact..."):
        try:
            pre_period, post_period = build_pre_post_periods(df, intervention_date)

            # CausalImpact espera a primeira coluna como y
            ci_df = df[["date", metric]].copy()
            ci_df = ci_df.set_index("date")

            # Rodar modelo (tfcausalimpact)
            ci = CausalImpact(ci_df, pre_period, post_period)

        except Exception as e:
            st.error(f"Erro ao rodar CausalImpact: {e}")
            st.stop()

        # -----------------------------
        # Saída – resumo
        # -----------------------------
        st.subheader("Resumo numérico")

        try:
            summary_table = ci.summary()  # tabela curta
            summary_report = ci.summary(output="report")  # texto longo
        except Exception as e:
            st.error(f"Erro ao gerar resumo: {e}")
            summary_table = None
            summary_report = None

        if summary_table is not None:
            st.text(summary_table)

        if summary_report is not None:
            with st.expander("Ver explicação detalhada (report textual)"):
                st.text(summary_report)

        # -----------------------------
        # Saída – gráfico
        # -----------------------------
        st.subheader("Gráfico do impacto causal")

        try:
            # Algumas versões retornam fig, outras desenham no gcf()
            fig = ci.plot()
            if fig is None:
                fig = plt.gcf()
            st.pyplot(fig)
            plt.close("all")
        except Exception as e:
            st.error(f"Erro ao gerar gráfico: {e}")
            st.info(
                "Mesmo sem o gráfico, o resumo numérico acima já mostra "
                "o impacto estimado da campanha."
            )
