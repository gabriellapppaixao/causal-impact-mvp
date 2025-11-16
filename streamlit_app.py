import io
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import streamlit as st


# -----------------------------
# Helpers
# -----------------------------
def load_csv(uploaded_file: io.BytesIO) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)

    # Descobre coluna de data
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
    if df.empty:
        raise ValueError("O CSV está vazio.")

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    if not (min_date <= intervention_date <= max_date):
        raise ValueError(
            f"A data de intervenção ({intervention_date}) precisa estar "
            f"dentro do intervalo de datas do CSV ({min_date} a {max_date})."
        )

    pre_end = date.fromordinal(intervention_date.toordinal() - 1)
    if pre_end < min_date:
        raise ValueError(
            "Período pré-intervenção ficou vazio. "
            "Escolha uma data de intervenção mais para frente."
        )

    pre_period = [min_date, pre_end]
    post_period = [intervention_date, max_date]
    return pre_period, post_period


def fit_forecast_structural(series: pd.Series, pre_period, post_period):
    """
    Ajusta um modelo simples de nível local (state-space) no pré
    e projeta o contrafactual no pós.
    """
    pre_start, pre_end = pre_period
    post_start, post_end = post_period

    # Index diário contínuo
    full_index = pd.date_range(series.index.min(), series.index.max(), freq="D")
    series = series.reindex(full_index)
    series = series.astype(float)
    series = series.fillna(method="ffill").fillna(method="bfill")

    pre_mask = (series.index.date >= pre_start) & (series.index.date <= pre_end)
    post_mask = (series.index.date >= post_start) & (series.index.date <= post_end)

    y_pre = series.loc[pre_mask]

    if len(y_pre) < 20:
        raise ValueError("Período pré muito curto (mínimo recomendado: 20 pontos).")

    # Modelo de nível local
    mod = sm.tsa.UnobservedComponents(y_pre, level="local level")
    res = mod.fit(disp=False)

    # Forecast no pós
    post_index = series.loc[post_mask].index
    n_post = len(post_index)
    if n_post == 0:
        raise ValueError("Período pós-intervenção está vazio.")

    forecast_res = res.get_forecast(steps=n_post)
    mean_fcst = forecast_res.predicted_mean
    ci_fcst = forecast_res.conf_int(alpha=0.05)

    # Dados observados no pós
    y_post = series.loc[post_mask]

    # Alinhar por segurança
    mean_fcst.index = post_index
    ci_fcst.index = post_index

    return y_pre, y_post, mean_fcst, ci_fcst


def summarize_effect(y_post, mean_fcst, ci_fcst):
    """
    Calcula efeito total e percentual, com IC aproximado.
    """
    # efeito ponto a ponto
    diff = y_post - mean_fcst

    # efeito total no período
    effect_total = diff.sum()
    expected_total = mean_fcst.sum()
    rel_effect = effect_total / expected_total if expected_total != 0 else np.nan

    # aproxima IC pro efeito total somando variâncias
    if "lower y" in ci_fcst.columns and "upper y" in ci_fcst.columns:
        # largura do intervalo ~ 4 * sigma (aprox), sigma ~ (upper-lower)/4
        sigma = (ci_fcst["upper y"] - ci_fcst["lower y"]) / 4.0
        var_total = np.sum(sigma**2)
        se_total = np.sqrt(var_total)
        z = 1.96
        lower_total = effect_total - z * se_total
        upper_total = effect_total + z * se_total
    else:
        lower_total = np.nan
        upper_total = np.nan

    return {
        "effect_total": effect_total,
        "expected_total": expected_total,
        "rel_effect": rel_effect,
        "lower_total": lower_total,
        "upper_total": upper_total,
    }


# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="Causal Impact MVP", layout="wide")

st.title("🔍 MVP – Calculadora de Impacto Causal (modelo próprio)")
st.write(
    """
    Este MVP estima o impacto de uma campanha comparando:

    **O que aconteceu** (série observada)  
    vs.  
    **O que teria acontecido sem a campanha** (contrafactual estimado por modelo de série temporal).

    Ele usa um modelo estrutural simples (nível local) da biblioteca `statsmodels` em vez da
    biblioteca oficial `CausalImpact` (que está incompatível com o ambiente do Streamlit Cloud).
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

# chute de data de intervenção no meio da série
mid_ordinal = (min_date.toordinal() + max_date.toordinal()) // 2
default_intervention = date.fromordinal(mid_ordinal)

intervention_date = st.date_input(
    "Data de início da campanha (intervenção)",
    value=default_intervention,
    min_value=min_date,
    max_value=max_date,
)

if st.button("🚀 Rodar análise de impacto"):

    with st.spinner("Rodando modelo de impacto causal..."):
        try:
            pre_period, post_period = build_pre_post_periods(df, intervention_date)

            series = df.set_index("date")[metric].astype(float)

            y_pre, y_post, mean_fcst, ci_fcst = fit_forecast_structural(
                series, pre_period, post_period
            )

            summary = summarize_effect(y_post, mean_fcst, ci_fcst)

        except Exception as e:
            st.error(f"Erro ao rodar a análise: {e}")
            st.stop()

    # -----------------------------
    # Resumo numérico
    # -----------------------------
    st.subheader("📊 Resumo do impacto")

    effect = summary["effect_total"]
    expected = summary["expected_total"]
    rel = summary["rel_effect"]
    lower = summary["lower_total"]
    upper = summary["upper_total"]

    st.markdown(
        f"""
        - Impacto total (período pós): **{effect:.2f}** unidades  
        - Valor esperado sem campanha: **{expected:.2f}** unidades  
        - Impacto relativo: **{rel*100:.1f}%**  

        Intervalo aproximado para o impacto total (95%):  
        - **{lower:.2f}** a **{upper:.2f}**
        """
    )

    # -----------------------------
    # Gráfico
    # -----------------------------
    st.subheader("📉 Observado vs. contrafactual")

    fig, ax = plt.subplots(figsize=(10, 4))

    # série completa
    full_series = series.copy()
    ax.plot(full_series.index, full_series.values, label="observado", linewidth=1.5)

    # contrafactual no pós
    ax.plot(mean_fcst.index, mean_fcst.values, label="contrafactual (sem campanha)", linestyle="--")

    # faixa de confiança
    if "lower y" in ci_fcst.columns and "upper y" in ci_fcst.columns:
        ax.fill_between(
            mean_fcst.index,
            ci_fcst["lower y"],
            ci_fcst["upper y"],
            alpha=0.2,
            label="IC 95% (contrafactual)",
        )

    ax.axvline(
        pd.to_datetime(intervention_date),
        color="red",
        linestyle=":",
        label="início campanha",
    )

    ax.set_xlabel("Data")
    ax.set_ylabel(metric)
    ax.legend()
    ax.grid(True, alpha=0.3)

    st.pyplot(fig)
    plt.close(fig)

    st.success("Análise concluída! ✅")
