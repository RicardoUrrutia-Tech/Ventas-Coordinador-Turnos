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

    # LEER RAW
    df_raw = pd.read_excel(file, header=None)

    # FILA 1 = FECHAS reales de cada columna
    fechas = df_raw.iloc[1].tolist()

    # Convertir todas las fechas excepto la primera (que es "Nombre")
    fechas = [fechas[0]] + list(pd.to_datetime(fechas[1:], errors="coerce"))

    # Ahora construir un DataFrame con FILA 2 EN ADELANTE, usando las fechas como encabezado
    df = df_raw.iloc[2:].copy()
    df.columns = fechas

    # Detectar columna de nombre (primer columna siempre)
    col_nombre = df.columns[0]

    # Diccionario final
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
# ASIGNACIÓN DE VENTAS
# ----------------------------------------------------------

def asignar_ventas(df_ventas, turnos, fecha_inicio, fecha_fin, franjas):

    df = df_ventas.copy()
    df["createdAt_local"] = pd.to_datetime(df["createdAt_local"])

    df = df[(df["createdAt_local"] >= fecha_inicio) & (df["createdAt_local"] <= fecha_fin)]

    if df.empty:
        return None, None, None, None

    registros = []

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

        # ASIGNACIÓN PROPORCIONAL
        if activos:
            m = monto / len(activos)
            for a in activos:
                registros.append({
                    "fecha": fecha,
                    "hora": hora,
                    "coordinador": a,
                    "venta_original": monto,
                    "coordinadores_activos": len(activos),
                    "venta_asignada": m
                })
        else:
            registros.append({
                "fecha": fecha,
                "hora": hora,
                "coordinador": None,
                "venta_original": monto,
                "coordinadores_activos": 0,
                "venta_asignada": 0
            })

    df_asignado = pd.DataFrame(registros)

    # Totales por coordinador
    df_totales = df_asignado[df_asignado["coordinador"].notna()] \
        .groupby("coordinador")["venta_asignada"].sum().reset_index()

    # Franjas
    def get_franja(h):
        for ini, fin in franjas:
            if hora_en_intervalo(h, ini, fin):
                return f"{ini.strftime('%H:%M')} - {fin.strftime('%H:%M')}"
        return "Fuera"

    df_asignado["franja"] = df_asignado["hora"].apply(get_franja)

    df_franjas = df_asignado[df_asignado["coordinador"].notna()] \
        .groupby(["coordinador", "franja"])["venta_asignada"].sum().reset_index()

    return df_asignado, df_totales, df_franjas, {}



