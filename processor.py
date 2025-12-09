import pandas as pd
from datetime import datetime, time


# ----------------------------------------------------------
# PARSER DE TURNOS
# ----------------------------------------------------------

def parse_turno(turno_raw):
    if pd.isna(turno_raw):
        return None
    turno_raw = str(turno_raw).strip()
    if turno_raw == "" or turno_raw.lower() == "libre":
        return None

    try:
        partes = turno_raw.split("-")
        ini = partes[0].strip().split(" ")[0]
        fin = partes[1].strip().split(" ")[0]

        h_ini = datetime.strptime(ini, "%H:%M:%S").time()
        h_fin = datetime.strptime(fin, "%H:%M:%S").time()

        return (h_ini, h_fin)
    except:
        return None


# ----------------------------------------------------------
# CARGA DE TURNOS POR FECHA REAL
# ----------------------------------------------------------

def load_turnos(file):

    df_raw = pd.read_excel(file, header=None)

    # Fila 1 = fechas
    fechas = df_raw.iloc[1].tolist()
    fechas = [fechas[0]] + list(pd.to_datetime(fechas[1:], errors="coerce"))

    # Crear DF con encabezados = fechas reales
    df = df_raw.iloc[2:].copy()
    df.columns = fechas

    # Primera columna es nombre
    col_nombre = df.columns[0]

    turnos = {}

    for _, row in df.iterrows():
        nombre = row[col_nombre]
        if pd.isna(nombre):
            continue

        turnos[nombre] = {}

        for col in df.columns[1:]:
            fecha = col.date()
            turno_raw = row[col]
            turno = parse_turno(turno_raw)
            turnos[nombre][fecha] = turno

    return turnos


# ----------------------------------------------------------
# UTILIDAD
# ----------------------------------------------------------

def hora_en_intervalo(h, h_ini, h_fin):
    if h_ini <= h_fin:
        return h_ini <= h <= h_fin
    return h >= h_ini or h <= h_fin


# ----------------------------------------------------------
# ASIGNACIÓN DE VENTAS POR TURNO
# ----------------------------------------------------------

def asignar_ventas(df_ventas, turnos, fecha_inicio, fecha_fin):

    df = df_ventas.copy()
    df["createdAt_local"] = pd.to_datetime(df["createdAt_local"])

    df = df[(df["createdAt_local"] >= fecha_inicio) & (df["createdAt_local"] <= fecha_fin)]

    if df.empty:
        return None, None, None

    registros = []

    # ------- ASIGNACIÓN DIARIA -------
    for _, row in df.iterrows():
        fecha = row["createdAt_local"].date()
        hora = row["createdAt_local"].time()
        monto = row["qt_price_local"]

        activos = []

        for persona, turnos_por_fecha in turnos.items():
            turno = turnos_por_fecha.get(fecha)
            if turno is None:
                continue

            h_ini, h_fin = turno

            if hora_en_intervalo(hora, h_ini, h_fin):
                activos.append(persona)

        # Asignación proporcional
        if activos:
            m = monto / len(activos)
            for a in activos:
                registros.append({
                    "fecha": fecha,
                    "hora": hora,
                    "coordinador": a,
                    "venta_original": monto,
                    "coordinadores_activos": len(activos),
                    "venta_asignada": m,
                    "turno": f"{h_ini.strftime('%H:%M')} - {h_fin.strftime('%H:%M')}"
                })
        else:
            registros.append({
                "fecha": fecha,
                "hora": hora,
                "coordinador": None,
                "venta_original": monto,
                "coordinadores_activos": 0,
                "venta_asignada": 0,
                "turno": "SIN TURNO"
            })

    df_asignado = pd.DataFrame(registros)

    # ----------------------------------------------------------
    # NUEVO: TOTAL POR COLABORADOR = (Bloques, Total Asignado)
    # ----------------------------------------------------------

    # Total asignado
    df_total_asignado = (
        df_asignado[df_asignado["coordinador"].notna()]
        .groupby("coordinador")["venta_asignada"]
        .sum()
        .reset_index()
    )

    # Bloques (turnos efectivos)
    bloques = []
    for persona, turnos_por_fecha in turnos.items():
        bloques_trabajados = sum(1 for t in turnos_por_fecha.values() if t is not None)
        bloques.append({"coordinador": persona, "Bloques": bloques_trabajados})

    df_bloques = pd.DataFrame(bloques)

    # Fusionar
    df_totales = df_total_asignado.merge(df_bloques, on="coordinador", how="left")
    df_totales.columns = ["Nombre", "Total Asignado", "Bloques"]

    return df_asignado, df_totales, bloques

