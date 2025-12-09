import streamlit as st
import pandas as pd
from datetime import datetime, time
import io
from processor import load_turnos, asignar_ventas

st.set_page_config(page_title="Asignación de Ventas por Turnos", layout="wide")

st.title("📊 Asignación de Ventas por Coordinador según Turnos (por fecha)")


# =====================================================
# 1) CARGA DE ARCHIVOS
# =====================================================

st.subheader("📁 Cargar Archivos")

turnos_file = st.file_uploader("Sube el archivo de TURNOS (por fecha del mes)", type=["xlsx"])
ventas_file = st.file_uploader("Sube el archivo de VENTAS", type=["xlsx"])


# =====================================================
# 2) SELECCIÓN DE FECHAS
# =====================================================

st.subheader("📅 Seleccionar rango de fechas para analizar")

col1, col2 = st.columns(2)
fecha_inicio = col1.date_input("Fecha de inicio")
fecha_fin = col2.date_input("Fecha de término")


# =====================================================
# 3) PROCESAR
# =====================================================

if st.button("🚀 Procesar"):

    if not turnos_file or not ventas_file:
        st.error("Debes subir ambos archivos para procesar.")
        st.stop()

    # -------------------------------------------------
    # LEER ARCHIVOS
    # -------------------------------------------------
    try:
        turnos = load_turnos(turnos_file)
        st.success("Turnos cargados correctamente.")
    except Exception as e:
        st.error(f"Error al cargar turnos: {e}")
        st.stop()

    try:
        df_ventas = pd.read_excel(ventas_file)
    except Exception as e:
        st.error(f"Error al leer archivo de ventas: {e}")
        st.stop()

    # -------------------------------------------------
    # FECHAS DE FILTRO
    # -------------------------------------------------
    fecha_i = datetime.combine(fecha_inicio, time(0, 0))
    fecha_f = datetime.combine(fecha_fin, time(23, 59))

    st.write(f"📌 Analizando ventas entre **{fecha_i}** y **{fecha_f}**.")

    # -------------------------------------------------
    # PROCESAMIENTO CENTRAL
    # -------------------------------------------------
    resultado = asignar_ventas(df_ventas, turnos, fecha_i, fecha_f)

    if resultado[0] is None:
        st.warning("No hay ventas en el rango seleccionado.")
        st.stop()

    df_asignado, df_totales, _ = resultado


    # =====================================================
    # 4) MOSTRAR RESULTADOS
    # =====================================================

    st.subheader("📄 Detalle de Ventas Asignadas")
    st.dataframe(df_asignado)

    st.subheader("👤 Totales por Coordinador (Bloques y Total Asignado)")
    st.dataframe(df_totales)


    # =====================================================
    # 5) DESCARGA EN EXCEL
    # =====================================================

    st.subheader("⬇️ Descargar reporte en Excel")

    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_asignado.to_excel(writer, sheet_name="Detalle", index=False)
        df_totales.to_excel(writer, sheet_name="Totales", index=False)

    st.download_button(
        label="Descargar reporte_final.xlsx",
        data=buffer.getvalue(),
        file_name="reporte_final.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.success("Proceso completado con éxito 🎉")
