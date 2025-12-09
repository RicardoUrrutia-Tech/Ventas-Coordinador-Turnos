import streamlit as st
import pandas as pd
from datetime import datetime, time
from processor import diagnosticar_turnos, load_turnos, asignar_ventas

st.title("🔍 Diagnóstico + Procesamiento de Turnos y Ventas")

turnos_file = st.file_uploader("Sube el archivo de TURNOS", type=["xlsx"])
ventas_file = st.file_uploader("Sube el archivo de VENTAS", type=["xlsx"])

# =======================================================
# 1️⃣ DIAGNÓSTICO DE TURNOS
# =======================================================

if turnos_file:
    st.header("🔬 Diagnóstico del archivo de Turnos")
    diag = diagnosticar_turnos(turnos_file)

    for key, df in diag.items():
        st.subheader(f"Resultado: {key}")
        st.write(df if isinstance(df, pd.DataFrame) else str(df))

    st.info("📌 Copia y pega estos resultados aquí en el chat para generar el processor final.")

# =======================================================
# 2️⃣ PROCESAMIENTO FINAL (se activará cuando generemos el processor final)
# =======================================================

if ventas_file and turnos_file:

    st.header("⚠️ Procesamiento desactivado hasta que confirmemos el formato del archivo.")
    st.warning("🛑 El processor final se generará después del diagnóstico.")
