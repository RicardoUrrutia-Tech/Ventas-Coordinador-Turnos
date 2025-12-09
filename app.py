import streamlit as st
import pandas as pd
from datetime import datetime, time
from processor import load_turnos, asignar_ventas

st.set_page_config(page_title="Asignación de Ventas", layout="wide")

st.title("📊 Asignación de Ventas por Coordinador según Turnos")

# ========================================
# 1) CARGA DE ARCHIVOS
# ========================================

st.subheader("📁 Cargar Archivos")

turnos_file = st.file_uploader("Sube el archivo de Turnos (formato por fecha)", type=["xlsx"])
ventas_file = st.file_uploader("Sube el archivo de Ventas", type=["xlsx"])

# ========================================
# 2) CONFIGURACIÓN DE FECHAS
# ========================================

st.subheader("📅 Seleccionar Rango de Fechas a Analizar")

col1, col2 = st.columns(2)
fecha_inicio = col1.date_input("Fecha de inicio")
fecha_fin = col2.date_input("Fecha de término")

# ========================================
# 3) DEFINICIÓN DE FRANJAS HORARIAS
# ========================================

st.subheader("⏰ Franjas Horarias")

franjas_default = [
    (time(0,0), time(6,0)),
    (time(6,0), time(12,0)),
    (time(12,0), time(18,0)),
    (time(18,0), time(23,59)),
]

st.info("Las franjas están predefinidas, pero puedo hacerlas editables si lo necesitas.")

franjas = franjas_default

# ========================================
# 4) PROCESAR DATOS
# ========================================

if st.button("🚀 Procesar"):

    # Validación de archivos
    if not turnos_file or not ventas_file:
        st.error("Debes cargar ambos archivos antes de procesar.")
        st.stop()

    # --------------------------
    # LEER ARCHIVOS
    # --------------------------
    st.subheader("📖 Leyendo archivos...")

    df_turnos_raw = turnos_file  # se entrega al processor
    df_ventas = pd.read_excel(ventas_file)

    # --------------------------
    # CARGAR TURNOS
    # --------------------------
    try:
        turnos = load_turnos(df_turnos_raw)
        st.success("Turnos cargados correctamente.")
    except Exception as e:
        st.error(f"Error al cargar turnos: {e}")
        st.stop()

    # --------------------------
    # PROCESAR VENTAS
    # --------------------------
    st.subheader("⚙️ Procesando ventas...")

    fecha_i = datetime.combine(fecha_inicio, time(0,0))
    fecha_f = datetime.combine(fecha_fin, time(23,59))

    resultado = asignar_ventas(df_ventas, turnos, fecha_i, fecha_f, franjas)

    if resultado[0] is None:
        st.warning("No hay ventas dentro del rango de fechas seleccionado.")
        st.stop()

    df_asignado, df_totales, df_franjas, resumen = resultado

    # ========================================
    # 5) MOSTRAR RESULTADOS
    # ========================================

    st.subheader("📄 Detalle de Ventas Asignadas")
    st.dataframe(df_asignado)

    st.subheader("👤 Total por Coordinador")
    st.dataframe(df_totales)

    st.subheader("⏰ Total por Franja Horaria")
    st.dataframe(df_franjas)

    # ========================================
    # 6) DESCARGAR RESULTADOS
    # ========================================

    st.subheader("⬇️ Descargar Resultado en Excel")

    output = pd.ExcelWriter("reporte_final.xlsx", engine="xlsxwriter")

    df_asignado.to_excel(output, sheet_name="Detalle", index=False)
    df_totales.to_excel(output, sheet_name="Totales", index=False)
    df_franjas.to_excel(output, sheet_name="Franjas", index=False)

    output.save()

    with open("reporte_final.xlsx", "rb") as f:
        st.download_button(
            label="Descargar reporte_final.xlsx",
            data=f,
            file_name="reporte_final.xlsx"
        )

    st.success("Proceso completado con éxito 🎉")
