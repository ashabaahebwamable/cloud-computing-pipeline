import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine
from sklearn.linear_model import LinearRegression

st.set_page_config(
    page_title="Global Patent Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .main .block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px;}
    h1 {color: #fafafa; font-weight: 700; letter-spacing: -0.02em;}
    h2, h3 {color: #fafafa; font-weight: 600;}
    [data-testid="stMetricValue"] {font-size: 2rem; font-weight: 700;}
    [data-testid="stMetricLabel"] {font-size: 0.85rem; color: #a0a8b4; text-transform: uppercase; letter-spacing: 0.05em;}
    [data-testid="stMetricDelta"] {font-size: 0.85rem;}
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(139,92,246,0.04) 100%);
        border: 1px solid rgba(99,102,241,0.15);
        border-radius: 12px;
        padding: 18px 20px;
    }
    .stTabs [data-baseweb="tab-list"] {gap: 8px;}
    .stTabs [data-baseweb="tab"] {
        height: 44px; padding: 0 22px;
        background-color: rgba(255,255,255,0.03);
        border-radius: 8px; font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
    }
    section[data-testid="stDataFrame"] {border-radius: 8px; overflow: hidden;}
</style>
""", unsafe_allow_html=True)

PALETTE = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981',
           '#06b6d4', '#3b82f6', '#84cc16', '#f43f5e', '#a855f7']
PRIMARY = '#6366f1'
SECONDARY = '#8b5cf6'
ACCENT = '#ec4899'
GREEN = '#10b981'
AMBER = '#f59e0b'

PLOTLY_TEMPLATE = dict(
    layout=dict(
        font=dict(family="Inter, system-ui, sans-serif", color="#e5e7eb"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        colorway=PALETTE,
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.1)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.1)"),
        margin=dict(l=10, r=10, t=30, b=10),
    )
)

DB_USER, DB_PWD, DB_HOST, DB_NAME = 'root', '', 'localhost', 'patent_db'
URL = (f'mysql+mysqlconnector://{DB_USER}@{DB_HOST}/{DB_NAME}' if not DB_PWD
       else f'mysql+mysqlconnector://{DB_USER}:{DB_PWD}@{DB_HOST}/{DB_NAME}')


@st.cache_resource
def get_engine():
    return create_engine(URL, pool_recycle=3600)


@st.cache_data(ttl=600)
def q(sql):
    return pd.read_sql_query(sql, get_engine())


def style_fig(fig, height=380, title=None):
    fig.update_layout(**PLOTLY_TEMPLATE['layout'], height=height,
                      title=dict(text=title or "", font=dict(size=14, color="#cbd5e1")))
    return fig


totals = q("""
SELECT
  (SELECT COUNT(*) FROM patents) AS patents,
  (SELECT COUNT(*) FROM inventors) AS inventors,
  (SELECT COUNT(*) FROM companies) AS companies,
  (SELECT COUNT(*) FROM relationships) AS relationships
""").iloc[0]

yearly = q("""
SELECT year, COUNT(*) AS patent_count
FROM patents WHERE year IS NOT NULL
GROUP BY year ORDER BY year
""")

top_companies = q("""
SELECT c.name, COUNT(r.patent_id) AS patent_count
FROM companies c JOIN relationships r ON c.company_id = r.company_id
GROUP BY c.company_id, c.name
ORDER BY patent_count DESC LIMIT 25
""")

top_inventors = q("""
SELECT i.inventor_id, i.name, i.country, COUNT(r.patent_id) AS patent_count
FROM inventors i JOIN relationships r ON i.inventor_id = r.inventor_id
GROUP BY i.inventor_id, i.name, i.country
ORDER BY patent_count DESC LIMIT 25
""")

countries = q("""
SELECT i.country, COUNT(DISTINCT r.patent_id) AS patent_count
FROM inventors i JOIN relationships r ON i.inventor_id = r.inventor_id
WHERE i.country IS NOT NULL AND i.country <> ''
GROUP BY i.country ORDER BY patent_count DESC
""")

country_year = q("""
SELECT p.year, i.country, COUNT(DISTINCT p.patent_id) AS patent_count
FROM patents p
JOIN relationships r ON p.patent_id = r.patent_id
JOIN inventors i ON r.inventor_id = i.inventor_id
WHERE i.country IS NOT NULL AND i.country <> '' AND p.year IS NOT NULL
GROUP BY p.year, i.country
""")

company_year = q("""
SELECT p.year, c.name, COUNT(DISTINCT p.patent_id) AS patent_count
FROM patents p
JOIN relationships r ON p.patent_id = r.patent_id
JOIN companies c ON r.company_id = c.company_id
WHERE c.name IS NOT NULL AND p.year IS NOT NULL
GROUP BY p.year, c.name
""")

recent_patents = q("""
SELECT patent_id, title, year
FROM patents ORDER BY year DESC, patent_id DESC LIMIT 300
""")


total_country_patents = countries['patent_count'].sum() or 1
countries['share_percent'] = (countries['patent_count'] / total_country_patents * 100).round(2)

yearly_calc = yearly.copy()
yearly_calc['previous_year_patents'] = yearly_calc['patent_count'].shift(1)
yearly_calc['yoy_change'] = yearly_calc['patent_count'] - yearly_calc['previous_year_patents']
yearly_calc['yoy_growth_rate'] = yearly_calc['yoy_change'] / yearly_calc['previous_year_patents']
yearly_calc['rolling_3yr_avg'] = yearly_calc['patent_count'].rolling(3).mean().round(1)
yearly_calc['cumulative'] = yearly_calc['patent_count'].cumsum()

latest_yoy = yearly_calc.dropna(subset=['yoy_growth_rate']).iloc[-1] if len(yearly_calc) > 1 else None

total_company_patents = top_companies['patent_count'].sum() or 1
top5_share = top_companies['patent_count'].head(5).sum() / total_company_patents
hhi = float(((top_companies['patent_count'] / total_company_patents) ** 2).sum())

if len(country_year) > 0 and country_year['year'].nunique() >= 6:
    yrs = sorted(country_year['year'].unique())
    recent_3, older_3 = yrs[-3:], yrs[-6:-3]
    rs = country_year[country_year['year'].isin(recent_3)].groupby('country')['patent_count'].sum()
    os_ = country_year[country_year['year'].isin(older_3)].groupby('country')['patent_count'].sum()
    rs, os_ = rs / rs.sum(), os_ / os_.sum()
    growth = (rs - os_).dropna().sort_values(ascending=False)
    fastest_country = growth.index[0] if len(growth) else None
    fastest_growth = growth.iloc[0] if len(growth) else None
else:
    fastest_country, fastest_growth = None, None

forecast_year, forecast_value = None, None
if len(yearly) >= 5:
    X = yearly['year'].values.reshape(-1, 1)
    y = yearly['patent_count'].values
    model = LinearRegression().fit(X, y)
    forecast_year = int(yearly['year'].max() + 1)
    forecast_value = max(0, int(model.predict([[forecast_year]])[0]))


st.markdown("# Global Patent Intelligence Dashboard")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Patents", f"{int(totals['patents']):,}")
c2.metric("Inventors", f"{int(totals['inventors']):,}")
c3.metric("Companies", f"{int(totals['companies']):,}")
c4.metric("Relationships", f"{int(totals['relationships']):,}")

st.markdown("### Analytics Overview")
o1, o2, o3, o4, o5 = st.columns(5)
if latest_yoy is not None and pd.notna(latest_yoy['yoy_growth_rate']):
    o1.metric("Latest YoY Growth",
              f"{latest_yoy['yoy_growth_rate']*100:.2f}%",
              delta=f"{int(latest_yoy['yoy_change']):+,} patents")
else:
    o1.metric("Latest YoY Growth", "—")
o2.metric("Top 5 Company Share", f"{top5_share*100:.2f}%")
o3.metric("Company HHI", f"{hhi:.4f}")
o4.metric("Fastest Country",
          fastest_country if fastest_country else "—",
          delta=f"{fastest_growth*100:+.2f}%" if fastest_growth is not None else None)
o5.metric("Forecast " + (str(forecast_year) if forecast_year else ""),
          f"{forecast_value:,}" if forecast_value else "—")

st.markdown("---")

tab_desc, tab_trends, tab_diag, tab_pred = st.tabs(
    ["Descriptive", "Trends", "Diagnostic", "Predictive"]
)


with tab_desc:
    st.markdown("### Descriptive Analytics")

    c1, c2 = st.columns([3, 2])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=yearly['year'], y=yearly['patent_count'],
            mode='lines', fill='tozeroy', line=dict(color=PRIMARY, width=2.5),
            fillcolor='rgba(99,102,241,0.15)', name='Patents'))
        st.plotly_chart(style_fig(fig, 380, "Patent Volume Trend by Year"),
                        use_container_width=True)
    with c2:
        top10c = countries.head(10)
        fig = px.bar(top10c, x='country', y='share_percent',
                     color='share_percent', color_continuous_scale='Plasma')
        fig.update_traces(marker_line_width=0)
        fig.update_layout(coloraxis_showscale=False, yaxis_title="Share %", xaxis_title="")
        st.plotly_chart(style_fig(fig, 380, "Top Countries by Patent Share"),
                        use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Recent yearly patent totals**")
        st.dataframe(yearly.tail(15), use_container_width=True, hide_index=True)
    with c2:
        st.markdown("**Country share table**")
        st.dataframe(countries.head(15), use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Top Inventors**")
        fig = px.bar(top_inventors.head(10).iloc[::-1],
                     x='patent_count', y='name', orientation='h',
                     color='patent_count', color_continuous_scale='Viridis')
        fig.update_traces(marker_line_width=0)
        fig.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="Patents")
        st.plotly_chart(style_fig(fig, 380), use_container_width=True)
    with c2:
        st.markdown("**Top Companies**")
        fig = px.bar(top_companies.head(10).iloc[::-1],
                     x='patent_count', y='name', orientation='h',
                     color='patent_count', color_continuous_scale='Magma')
        fig.update_traces(marker_line_width=0)
        fig.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="Patents")
        st.plotly_chart(style_fig(fig, 380), use_container_width=True)

    st.markdown("**Recent Patent Records**")
    n_rows = st.slider("Number of rows to show", 5, 200, 25, 5)
    st.dataframe(recent_patents.head(n_rows), use_container_width=True, hide_index=True)


with tab_trends:
    st.markdown("### Trends Across Time")

    decades = yearly.copy()
    decades['decade'] = (decades['year'] // 10 * 10).astype(int)
    decade_totals = decades.groupby('decade', as_index=False)['patent_count'].sum()
    decade_totals['decade_label'] = decade_totals['decade'].astype(str) + 's'

    c1, c2 = st.columns([3, 2])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=yearly_calc['year'], y=yearly_calc['cumulative'],
            mode='lines', line=dict(color=SECONDARY, width=2.5),
            fill='tozeroy', fillcolor='rgba(139,92,246,0.18)', name='Cumulative'))
        st.plotly_chart(style_fig(fig, 360, "Cumulative Patents Over Time"),
                        use_container_width=True)
    with c2:
        fig = px.bar(decade_totals, x='decade_label', y='patent_count',
                     color='patent_count', color_continuous_scale='Sunset')
        fig.update_traces(marker_line_width=0)
        fig.update_layout(coloraxis_showscale=False, xaxis_title="", yaxis_title="Patents")
        st.plotly_chart(style_fig(fig, 360, "Patents by Decade"),
                        use_container_width=True)

    top5_countries = countries.head(5)['country'].tolist()
    cyear_top = country_year[country_year['country'].isin(top5_countries)].copy()
    cyear_top = cyear_top.sort_values(['country', 'year'])

    c1, c2 = st.columns(2)
    with c1:
        fig = px.area(cyear_top, x='year', y='patent_count', color='country',
                      color_discrete_sequence=PALETTE)
        fig.update_layout(legend=dict(orientation="h", y=1.12, x=0))
        st.plotly_chart(style_fig(fig, 380, "Top 5 Countries — Patent Trends"),
                        use_container_width=True)
    with c2:
        fig = go.Figure()
        for i, country in enumerate(top5_countries):
            d = cyear_top[cyear_top['country'] == country].sort_values('year')
            fig.add_trace(go.Scatter(
                x=d['year'], y=d['patent_count'],
                mode='lines', name=country,
                line=dict(width=2.2, color=PALETTE[i % len(PALETTE)])))
        fig.update_layout(legend=dict(orientation="h", y=1.12, x=0))
        st.plotly_chart(style_fig(fig, 380, "Top 5 Countries — Line View"),
                        use_container_width=True)

    top10_companies = top_companies.head(10)['name'].tolist()
    coy = company_year[company_year['name'].isin(top10_companies)].copy()
    fig = px.line(coy.sort_values('year'), x='year', y='patent_count',
                  color='name', color_discrete_sequence=PALETTE)
    fig.update_layout(legend=dict(orientation="h", y=-0.15, x=0))
    fig.update_traces(line=dict(width=2))
    st.plotly_chart(style_fig(fig, 420, "Top 10 Companies — Annual Filings"),
                    use_container_width=True)

    pivot = country_year[country_year['country'].isin(countries.head(8)['country'])]
    pivot = pivot.pivot(index='country', columns='year', values='patent_count').fillna(0)
    pivot = pivot.loc[countries.head(8)['country'].tolist()]
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale='Inferno', hovertemplate='%{y} — %{x}<br>%{z:,} patents<extra></extra>'))
    st.plotly_chart(style_fig(fig, 360, "Country × Year Heatmap (Top 8 Countries)"),
                    use_container_width=True)


with tab_diag:
    st.markdown("### Diagnostic Analytics")

    c1, c2 = st.columns(2)
    with c1:
        d = yearly_calc.dropna(subset=['yoy_growth_rate']).copy()
        d['yoy_pct'] = d['yoy_growth_rate'] * 100
        d['color'] = d['yoy_pct'].apply(lambda x: GREEN if x >= 0 else ACCENT)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=d['year'], y=d['yoy_pct'], marker_color=d['color'],
                             marker_line_width=0))
        fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_width=1)
        fig.update_layout(yaxis_title="YoY Growth %", xaxis_title="")
        st.plotly_chart(style_fig(fig, 380, "Year-over-Year Growth Rate"),
                        use_container_width=True)
    with c2:
        top20 = top_companies.head(20).copy()
        top20['portfolio_share_%'] = (top20['patent_count'] / total_company_patents * 100).round(2)
        fig = px.bar(top20, x='name', y='portfolio_share_%',
                     color='portfolio_share_%', color_continuous_scale='Turbo')
        fig.update_traces(marker_line_width=0)
        fig.update_layout(coloraxis_showscale=False,
                          xaxis_tickangle=-60, yaxis_title="Share %", xaxis_title="")
        st.plotly_chart(style_fig(fig, 380, "Top 20 Companies — Portfolio Share"),
                        use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=yearly_calc['year'], y=yearly_calc['patent_count'],
            mode='lines', name='Annual', line=dict(color=PRIMARY, width=1.5),
            opacity=0.45))
        fig.add_trace(go.Scatter(
            x=yearly_calc['year'], y=yearly_calc['rolling_3yr_avg'],
            mode='lines', name='3-yr rolling avg',
            line=dict(color=AMBER, width=2.8)))
        fig.update_layout(legend=dict(orientation="h", y=1.12, x=0))
        st.plotly_chart(style_fig(fig, 360, "Annual vs 3-Year Rolling Average"),
                        use_container_width=True)
    with c2:
        st.markdown("**Yearly diagnostics**")
        diag = yearly_calc.copy()
        diag['yoy_growth_rate'] = (diag['yoy_growth_rate'] * 100).round(2)
        st.dataframe(
            diag.tail(15)[['year', 'patent_count', 'yoy_change',
                           'yoy_growth_rate', 'rolling_3yr_avg']],
            use_container_width=True, hide_index=True)

    st.markdown("**Company concentration**")
    conc = top_companies.head(15).copy()
    conc['portfolio_share_%'] = (conc['patent_count'] / total_company_patents * 100).round(2)
    conc['cumulative_share_%'] = conc['portfolio_share_%'].cumsum().round(2)
    st.dataframe(conc, use_container_width=True, hide_index=True)


with tab_pred:
    st.markdown("### Predictive Analytics")

    if len(yearly) >= 5:
        X = yearly['year'].values.reshape(-1, 1)
        y = yearly['patent_count'].values
        model = LinearRegression().fit(X, y)
        future_years = np.arange(yearly['year'].max() + 1, yearly['year'].max() + 6)
        future_pred = np.maximum(model.predict(future_years.reshape(-1, 1)), 0)
        fitted = model.predict(X)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=yearly['year'], y=y, mode='lines',
            name='Actual', line=dict(color=PRIMARY, width=2.5),
            fill='tozeroy', fillcolor='rgba(99,102,241,0.12)'))
        fig.add_trace(go.Scatter(
            x=yearly['year'], y=fitted, mode='lines',
            name='Linear fit', line=dict(color=SECONDARY, dash='dash', width=2)))
        fig.add_trace(go.Scatter(
            x=future_years, y=future_pred, mode='lines+markers',
            name='5-year forecast',
            line=dict(color=AMBER, width=3),
            marker=dict(size=10, color=AMBER, line=dict(width=2, color='#1f2937'))))
        fig.update_layout(legend=dict(orientation="h", y=1.12, x=0),
                          xaxis_title="Year", yaxis_title="Patents")
        st.plotly_chart(style_fig(fig, 440, "Patent Volume — Actual vs Forecast"),
                        use_container_width=True)

        c1, c2 = st.columns([2, 1])
        with c1:
            ft = pd.DataFrame({'year': future_years,
                               'forecast': future_pred.round().astype(int)})
            fig = px.bar(ft, x='year', y='forecast',
                         color='forecast', color_continuous_scale='Cividis')
            fig.update_traces(marker_line_width=0)
            fig.update_layout(coloraxis_showscale=False, xaxis_title="", yaxis_title="Predicted patents")
            st.plotly_chart(style_fig(fig, 320, "5-Year Forecast"),
                            use_container_width=True)
        with c2:
            r2 = model.score(X, y)
            st.metric("Model R²", f"{r2:.3f}")
            st.metric("Slope (patents/year)", f"{model.coef_[0]:+.1f}")
            st.dataframe(ft, use_container_width=True, hide_index=True)

    else:
        st.info("Need at least 5 years of data for forecasting.")
