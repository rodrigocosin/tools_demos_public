import os
import streamlit as st
import pandas as pd
from databricks.sdk import WorkspaceClient

WAREHOUSE_ID = "0c2def7684630e5e"
IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))

@st.cache_resource
def get_client():
    if IS_DATABRICKS_APP:
        return WorkspaceClient()
    return WorkspaceClient(profile="fe-vm-cosin-aws-serverless")

st.title("SQL Select Tester")

query = st.text_area("Query SQL", value="SELECT * FROM samples.nyctaxi.trips LIMIT 10", height=120)

if st.button("Executar"):
    try:
        w = get_client()
        result = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement=query,
            wait_timeout="50s",
        )
        state = result.status.state.value if result.status and result.status.state else "UNKNOWN"
        if state != "SUCCEEDED":
            msg = result.status.error.message if result.status and result.status.error else state
            st.error(f"Query falhou ({state}): {msg}")
        else:
            schema = result.manifest.schema.columns
            cols = [c.name for c in schema]
            rows = list(result.result.data_array) if result.result and result.result.data_array else []
            df = pd.DataFrame(rows, columns=cols)
            st.success(f"{len(df)} linhas retornadas")
            st.dataframe(df)
    except Exception as e:
        st.error(f"Erro: {e}")
