import streamlit as st
import pandas as pd
from causalimpact import CausalImpact
import matplotlib.pyplot as plt
import io

st.set_page_config(
    page_title="Calculadora de Causal Impact - MVP",
    layout="wide"
)

st.title("📈 Calculadora de Causal Impact – MVP")

st.markdown(
    """
Esta ferramenta permite analisar o impacto **causal** de uma campanha em uma série temporal.

**Passos:**
1. Faça upload de um CSV com uma coluna `date` e pelo menos uma métrica (target).
2. Selecione a métrica alvo (target) e, opcionalmente, séries de controle.
3. Defina o período **pré** e **pós** intervenção.
4. Clique em **Rodar análise**.
"""
)

uploaded = st.file_uploader("📁 Upload do arquivo CSV", type=["csv"])

if uploaded is not None:
    # ---- Leitura e preparação do CSV ----
    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Erro ao ler o CSV: {e}")
        st.stop()

    if "date" not in df.columns:
        st.error("O CSV precisa ter uma coluna chamada `date` (YYYY-MM-DD).")
        st.stop()

    try:
        df["date"] = pd.to_datetime(df["date"])
    except Exception as e:
        st.error(f"Erro ao converter a coluna `date` para datetime: {e}")
        st.stop()

    df = df.set_index("date").sort_index()

    if df.empty:
        st.error("O DataFrame está vazio após o processamento.")
        st.stop()

    # Garante que temos TODAS as datas entre min e max (sem buracos)
    full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D")
    df = df.reindex(full_index)
    df.index.name = "date"

    # Preenche NAs simples
    df = df.fillna(method="ffill").fillna(method="bfill")

    st.subheader("🔍 Preview dos dados")
    st.dataframe(df.head())

    # ---- Seleção de colunas numéricas ----
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        st.error("Não foram encontradas colunas numéricas para usar como métricas.")
        st.stop()

    target = st.selectbox("🎯 Selecione a métrica alvo (target)", numeric_cols)
    controls = st.multiselect(
        "📊 Selecione séries de controle (opcional)",
        [c for c in numeric_cols if c != target]
    )

    min_date = df.index.min().date()
    max_date = df.index.max().date()
    st.markdown(f"📆 Intervalo disponível nos dados: **{min_date}** até **{max_date}**")

    col1, col2 = st.columns(2)
    with col1:
        pre_start = st.date_input("Pré-período: início", value=min_date,
                                  min_value=min_date, max_value=max_date)
        pre_end = st.date_input("Pré-período: fim", value=min_date,
                                min_value=min_date, max_value=max_date)
    with col2:
        post_start = st.date_input("Pós-período: início", value=max_date,
                                   min_value=min_date, max_value=max_date)
        post_end = st.date_input("Pós-período: fim", value=max_date,
                                 min_value=min_date, max_value=max_date)

    if st.button("🚀 Rodar análise de Causal Impact"):
        # ---- Validações de datas ----
        if pre_start >= pre_end:
            st.error("O fim do pré-período deve ser depois do início.")
            st.stop()
        if post_start >= post_end:
            st.error("O fim do pós-período deve ser depois do início.")
            st.stop()
        if pre_end >= post_start:
            st.error("O pré-período deve terminar antes do início do pós-período.")
            st.stop()

        cols_for_model = [target] + controls
        df_ci = df[cols_for_model].copy()

        # periods em formato de string, como a lib espera
        pre_period = [pre_start.strftime("%Y-%m-%d"), pre_end.strftime("%Y-%m-%d")]
        post_period = [post_start.strftime("%Y-%m-%d"), post_end.strftime("%Y-%m-%d")]

        st.info(
            f"Rodando CausalImpact com pré-período {pre_period} "
            f"e pós-período {post_period}..."
        )

        # ---- Rodar CausalImpact ----
        try:
            ci = CausalImpact(df_ci, pre_period, post_period)
        except Exception as e:
            st.error(f"Erro ao rodar CausalImpact: {e}")
            st.stop()

        # ---- Summary ----
        st.subheader("📊 Summary")
        try:
            st.text(ci.summary())
        except Exception as e:
            st.error(f"Erro ao gerar summary: {e}")
        # ---- Report ----
        st.subheader("📝 Report")
        try:
            st.text(ci.summary(output="report"))
        except Exception as e:
            st.error(f"Erro ao gerar report: {e}")

        # ---- Plot ----
        st.subheader("📉 Gráfico Observado vs. Contrafactual")
        try:
            fig = ci.plot()
            st.pyplot(fig)

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150)
            st.download_button(
                label="⬇️ Baixar gráfico em PNG",
                data=buf.getvalue(),
                file_name="causalimpact_plot.png",
                mime="image/png"
            )
        except Exception as e:
            st.error(f"Erro ao gerar o gráfico: {e}")

        st.success("Análise concluída (ou pelo menos rodou sem quebrar 😅).")

else:
    st.info("Faça upload de um arquivo CSV para começar.")
