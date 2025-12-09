import pandas as pd
from datetime import datetime, time

# ----------------------------------------------------------
# PARSER
# ----------------------------------------------------------

def parse_turno(turno_raw):
    if pd.isna(turno_raw):
        return None
    turno_raw = str(turno_raw).strip()
    if turno_raw.lower() == "libre" or turno_raw == "":
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
# CARGA REAL DE TURNOS (POR FECHA, NO POR DÍA SEMANA)
# ----------------------------------------------------------

def load_turnos(df_raw):

    # El encabezado real está en la FILA 2
    df = pd.read_excel(df_raw, header=2)

    # Detectar columna Nombre
    col_nombre = [c for c in df.columns if "nombre" in str(c).lower()][0]

    # El resto de columnas son fechas
    columnas_fechas = [c for c in df.columns if c != col_nombre]

    # Convertir encabezados a fechas reales
    fechas = pd.to_datetime([df.columns[idx+1] for idx in range(len(columnas_fechas))], errors="coerce")

    # Diccionario final
    turnos = {}

    for _, row in df.iterrows():
        nombre = row[col_nombre]
        turnos[nombre] = {}

        for idx, col in enumerate(columnas_fechas):

            fecha = fechas[idx]

            turno = parse_turno(row[col])

            turnos[nombre][fecha.date()] = turno

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

    # Filtrar por rango
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

            if fecha not in turnos_por_fecha:
                continue

            turno = turnos_por_fecha[fecha]

            if turno is None:
                continue

            h_ini, h_fin = turno

            if hora_en_intervalo(hora, h_ini, h_fin):
                activos.append(persona)

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

    df_totales = df_asignado[df_asignado["coordinador"].notna()].groupby("coordinador")["venta_asignada"].sum().reset_index()

    # FRANJAS
    def get_franja(h):
        for ini, fin in franjas:
            if hora_en_intervalo(h, ini, fin):
                return f"{ini.strftime('%H:%M')} - {fin.strftime('%H:%M')}"
        return "Fuera"

    df_asignado["franja"] = df_asignado["hora"].apply(get_franja)

    df_franjas = df_asignado[df_asignado["coordinador"].notna()] \
        .groupby(["coordinador", "franja"])["venta_asignada"].sum().reset_index()

    return df_asignado, df_totales, df_franjas, {}


