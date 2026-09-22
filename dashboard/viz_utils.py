# -*- coding: utf-8 -*-
"""
viz_utils.py
==============
Funksione vizuale të përbashkëta (gauge charts) -- përdoren nga
page_patient.py dhe page_new_patient.py.
"""
import plotly.graph_objects as go

GAUGE_COLOR = {
    "Low": "#2e7d32", "Normal": "#2e7d32",
    "Medium": "#f9a825", "Kufitar": "#f9a825",
    "Kufitar (pre-hipertension)": "#f9a825", "Prediabet": "#f9a825",
    "High": "#c62828", "I lartë": "#c62828", "Diabetik": "#c62828",
}
ORDER_3 = {"Low": 33, "Medium": 66, "High": 100,
           "Normal": 20, "Kufitar": 60, "Kufitar (pre-hipertension)": 60,
           "I lartë": 95, "Prediabet": 60, "Diabetik": 95}


def gauge(title, category):
    val = ORDER_3.get(category, 50)
    color = GAUGE_COLOR.get(category, "#616161")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={"font": {"size": 1}},
        title={"text": f"{title}<br><span style='font-size:0.7em'>{category}</span>"},
        gauge={
            "axis": {"range": [0, 100], "visible": False},
            "bar": {"color": color},
            "bgcolor": "#eeeeee",
            "steps": [
                {"range": [0, 40], "color": "#e8f5e9"},
                {"range": [40, 75], "color": "#fff8e1"},
                {"range": [75, 100], "color": "#ffebee"},
            ],
        },
    ))
    fig.update_layout(height=220, margin=dict(t=60, b=10, l=20, r=20))
    return fig
