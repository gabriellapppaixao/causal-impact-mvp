import streamlit as st
import pandas as pd
from causalimpact import CausalImpact
import matplotlib.pyplot as plt
import io

# -------------------------------------------------------
# Configuração da página
# -------------------------------------------------------
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

# -------------------------------------------------------
# Upload do CSV
# -------------------------------------------------------
uploaded = st.file_uploader("📁 Upload do arquivo CSV", type=["csv"])

if uploaded is None:
    st.info("Faça upload de um arquivo CSV para começar.")
    st.stop()

# -------------------------------------------------------
# Leitura do arquivo
# -------------------------------------------------------
try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"Erro ao ler o CSV: {e}")
    st.stop()

# validação da coluna date
if "date" not in df.columns:
    st.error("O CSV precisa ter uma coluna chamada `date`.")
    st.stop()

# conversão da data
try:
    df["date"] = pd.to_datetime(df["date"])
except Exception as e:
    st.error(f"Erro ao converter a coluna `date` para datetime: {e}")
    st.stop()

# colocar date como índice
df = df.set_index("date").sort_index()

if df.empty:
    st.error("O CSV está vazio após processamento.")
    st.stop()

# garantir série contínua diária
full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D")
df = df.reindex(full_index)
df.index.name = "date"

# preencher NAs
df = df.fillna(method="ffill").fillna(method="bfill")

# -------------------------------------------------------
# Preview
# -------------------------------------------------------
st.subheader("🔍 Preview dos dados")
st.dataframe(df.head())

# -------------------------------------------------------
# Seleção de colunas numéricas
# -------------------------------------------------------
numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
if not numeric_cols:
    st.error("Não há colunas numéricas para usar como métrica.")
    st.stop()

target = st.selectbox("🎯 Métrica alvo (target)", numeric_cols)
controls = st.multiselect(
    "📊 Séries de controle (opcional)",
    [c for c in numeric_cols if c != target]
)

# -------------------------------------------------------
# Períodos disponíveis
# -------------------------------------------------------
min_date = df.index.min().date()
max_date = df.index.max().date()
st.markdown(f"📆 **Datas disponíveis:** {min_date} → {max_date}")

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

# -------------------------------------------------------
# BOTÃO – Rodar análise
# -------------------------------------------------------
if st.button("🚀 Rodar análise de Causal Impact"):

    # validações
    if pre_start >= pre_end:
        st.error("O pré-período precisa terminar depois de começar.")
        st.stop()

    if post_start >= post_end:
        st.error("O pós-período precisa terminar depois de começar.")
        st.stop()

    if pre_end >= post_start:
        st.error("O pré-período deve terminar **ANTES** do início do pós-período.")
        st.stop()

    # preparar DF
    cols_for_model = [target] + controls
    df_ci = df[cols_for_model].copy()

    df_ci = df_ci.fillna(method="ffill").fillna(method="bfill")

    # períodos em formato aceito pela lib
    pre_period = [pre_start.strftime("%Y-%m-%d"), pre_end.strftime("%Y-%m-%d")]
    post_period = [post_start.strftime("%Y-%m-%d"), post_end.strftime("%Y-%m-%d")]

    st.info(f"Rodando modelo CausalImpact…\nPré: {pre_period}\nPós: {post_period}")

    # -------------------------------------------------------
    # Rodar modelo corretamente
    # -------------------------------------------------------
    try:
        ci = CausalImpact(df_ci, pre_period, post_period)
        ci.run()   # <<< ESSENCIAL – sem isso a lib quebra
    except Exception as e:
        st.error(f"Erro ao rodar CausalImpact: {e}")
        st.stop()

    # -------------------------------------------------------
    # Summary
    # -------------------------------------------------------
    st.subheader("📊 Summary")
    try:
        st.text(ci.summary())
    except Exception as e:
        st.error(f"Erro ao gerar summary: {e}")

    # -------------------------------------------------------
    # Report
    # -------------------------------------------------------
    st.subheader("📝 Report")
    try:
        st.text(ci.summary(output="report"))
    except Exception as e:
        st.error(f"Erro ao gerar report: {e}")

    # -------------------------------------------------------
    # Plot
    # -------------------------------------------------------
    st.subheader("📉 Gráfico Observado vs. Contrafactual")
    try:
        fig = ci.plot()
        st.pyplot(fig)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150)

        st.download_button(
            label="⬇️ Baixar gráfico",
            data=buf.getvalue(),
            file_name="causalimpact.png",
            mime="image/png"
        )
    except Exception as e:
        st.error(f"Erro ao gerar gráfico: {e}")

    st.success("Análise concluída! ✅")
