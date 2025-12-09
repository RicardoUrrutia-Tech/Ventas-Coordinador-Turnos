import streamlit as st
import pandas as pd
from datetime import datetime, time
from processor import load_turnos, asignar_ventas

# -----------------------------------------------
#   CONFIGURACIÓN DE LA APP
# -----------------------------------------------
st.title("Asignación de Ventas por Coordinador")
st.write("Carga los archivos, selecciona fechas y obtén el reporte en Excel.")

# -----------------------------------------------
#   CARGA DE ARCHIVOS
# -----------------------------------------------
turnos_file = st.file_uploader("Sube el archivo de Turnos (.xlsx)", type=["xlsx"])
ventas_file = st.file_uploader("Sube el archivo de Ventas (.xlsx)", type=["xlsx"])

# -----------------------------------------------
#   FILTRO DE FECHAS
# -----------------------------------------------
col1, col2 = st.columns(2)
fecha_inicio = col1.date_input("Fecha inicio")
fecha_fin = col2.date_input("Fecha término")

# -----------------------------------------------
#   DEFINICIÓN DE FRANJAS HORARIAS
# -----------------------------------------------
st.subheader("Franjas Horarias (modificables)")

default_franjas = [
    (time(0,0), time(6,0)),
    (time(6,0), time(12,0)),
    (time(12,0), time(18,0)),
    (time(18,0), time(23,59))
]

franjas = default_franjas

# -----------------------------------------------
#   PROCESAR
# -----------------------------------------------
if st.button("Procesar"):

    if not turnos_file or not ventas_file:
        st.error("Por favor sube ambos archivos.")
        st.stop()

    df_turnos = pd.read_excel(turnos_file)
    df_ventas = pd.read_excel(ventas_file)

    turnos = load_turnos(df_turnos)

    resultado = asignar_ventas(
        df_ventas,
        turnos,
        datetime.combine(fecha_inicio, time(0,0)),
        datetime.combine(fecha_fin, time(23,59)),
        franjas
    )

    if resultado[0] is None:
        st.warning("No hay ventas en el rango de fechas seleccionado.")
        st.stop()

    df_asignado, df_totales, df_franjas, resumen_global = resultado

    st.success("Procesamiento completado.")

    # Mostrar tablas
    st.subheader("Ventas Asignadas (detalle)")
    st.dataframe(df_asignado)

    st.subheader("Totales por Coordinador")
    st.dataframe(df_totales)

    st.subheader("Totales por Franja Horaria")
    st.dataframe(df_franjas)

    st.subheader("Resumen Global")
    st.json(resumen_global)

    # DESCARGA EN EXCEL
    output = pd.ExcelWriter("reporte_asignacion.xlsx", engine="xlsxwriter")
    df_asignado.to_excel(output, sheet_name="Detalle", index=False)
    df_totales.to_excel(output, sheet_name="Totales", index=False)
    df_franjas.to_excel(output, sheet_name="Franjas", index=False)
    output.save()

    with open("reporte_asignacion.xlsx", "rb") as f:
        st.download_button(
            label="Descargar Excel",
            data=f,
            file_name="reporte_asignacion.xlsx"
        )
