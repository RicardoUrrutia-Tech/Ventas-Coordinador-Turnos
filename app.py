import streamlit as st
import processor_diag as diag

st.title("🔍 Diagnóstico de archivo de turnos")
st.write("Esta app mostrará cómo Pandas está leyendo tu archivo exactamente.")

turnos_file = st.file_uploader("Sube tu archivo de turnos (.xlsx)", type=["xlsx"])

if turnos_file:
    st.success("Archivo recibido. Analizando...")
    diag.debug_read_turnos(turnos_file)

