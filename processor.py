import pandas as pd
import streamlit as st

def debug_read_turnos(file):
    """
    Solo lectura sin procesar: muestra cómo Pandas interpreta el archivo.
    """
    st.write("=== LECTURA RAW SIN HEADER ===")
    df_raw = pd.read_excel(file, header=None)
    st.write(df_raw.head(15))

    st.write("Forma:", df_raw.shape)
    st.write("Primeras columnas detectadas:", df_raw.columns.tolist())

    st.write("=== LECTURA NORMAL (header=0) ===")
    df_header0 = pd.read_excel(file, header=0)
    st.write(df_header0.head())

    st.write("Columnas detectadas (header=0):", df_header0.columns.tolist())

    st.write("=== LECTURA (header=1) ===")
    try:
        df_header1 = pd.read_excel(file, header=1)
        st.write(df_header1.head())
        st.write("Columnas detectadas (header=1):", df_header1.columns.tolist())
    except:
        st.write("header=1 generó error")

    st.write("=== LECTURA (header=2) ===")
    try:
        df_header2 = pd.read_excel(file, header=2)
        st.write(df_header2.head())
        st.write("Columnas detectadas (header=2):", df_header2.columns.tolist())
    except:
        st.write("header=2 generó error")

    st.write("=== LECTURA (header=3) ===")
    try:
        df_header3 = pd.read_excel(file, header=3)
        st.write(df_header3.head())
        st.write("Columnas detectadas (header=3):", df_header3.columns.tolist())
    except:
        st.write("header=3 generó error")

    return df_raw

