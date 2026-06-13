import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import os
import re
from groq import Groq

from schema import SCHEMA, EXAMPLE_QUESTIONS
from database import create_database

load_dotenv()
create_database()

DB_PATH = "data/superstore.db"

st.set_page_config(
    page_title="SQL Chatbot — Superstore",
    page_icon="🛒",
    layout="wide"
)

st.title("Superstore SQL Chatbot")
st.caption("Ask any business question in plain English — powered by Groq + Llama")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "query_history" not in st.session_state:
    st.session_state.query_history = []

def generate_sql(question: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SCHEMA},
            {"role": "user", "content": question}
        ],
        temperature=0,
        max_tokens=500,
    )
    sql = response.choices[0].message.content.strip()
    sql = re.sub(r"```sql|```", "", sql).strip()
    return sql

def is_safe_query(sql: str) -> bool:
    forbidden = ["drop", "delete", "update", "insert", "alter", "create", "truncate"]
    return not any(word in sql.lower() for word in forbidden)

def run_query(sql: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def auto_chart(df: pd.DataFrame, question: str):
    if df.empty or len(df.columns) < 2:
        return None
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include="object").columns.tolist()
    if not numeric_cols:
        return None
    x_col = text_cols[0] if text_cols else df.columns[0]
    y_col = numeric_cols[0]
    question_lower = question.lower()
    if any(w in question_lower for w in ["trend", "monthly", "yearly", "over time", "by month", "by year"]):
        fig = px.line(df, x=x_col, y=y_col, markers=True, title=f"{y_col} over {x_col}")
    elif len(df) <= 15:
        fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}",
                     color=y_col, color_continuous_scale="Blues")
    else:
        fig = px.bar(df, x=y_col, y=x_col, orientation="h", title=f"{y_col} by {x_col}")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=20, l=20, r=20),
        height=400
    )
    return fig

with st.sidebar:
    st.subheader("Try these questions")
    for q in EXAMPLE_QUESTIONS:
        if st.button(q, use_container_width=True, key=q):
            st.session_state.pending_question = q
    st.divider()
    st.subheader("Query history")
    if st.session_state.query_history:
        for i, item in enumerate(reversed(st.session_state.query_history[-5:])):
            with st.expander(f"Query {len(st.session_state.query_history) - i}"):
                st.code(item, language="sql")
    else:
        st.caption("No queries yet")
    st.divider()
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.query_history = []
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            if "sql" in msg:
                with st.expander("Generated SQL"):
                    st.code(msg["sql"], language="sql")
            if "df" in msg:
                st.dataframe(msg["df"], use_container_width=True)
            if "chart" in msg and msg["chart"] is not None:
                st.plotly_chart(msg["chart"], use_container_width=True)
            if "error" in msg:
                st.error(msg["error"])
        else:
            st.write(msg["content"])

question = st.chat_input("Ask a question about the Superstore data...")

if "pending_question" in st.session_state:
    question = st.session_state.pending_question
    del st.session_state.pending_question

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        with st.spinner("Generating SQL..."):
            try:
                sql = generate_sql(question)
                if not is_safe_query(sql):
                    st.error("Query blocked — only SELECT queries are allowed.")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "error": "Query blocked — only SELECT queries are allowed."
                    })
                else:
                    with st.expander("Generated SQL"):
                        st.code(sql, language="sql")
                    df = run_query(sql)
                    chart = auto_chart(df, question)
                    st.dataframe(df, use_container_width=True)
                    if chart:
                        st.plotly_chart(chart, use_container_width=True)
                    st.session_state.query_history.append(sql)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "sql": sql,
                        "df": df,
                        "chart": chart
                    })
            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "error": f"Something went wrong: {str(e)}"
                })