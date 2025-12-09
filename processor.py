import pandas as pd
from datetime import datetime, time, timedelta

# ----------------------------------------------------------
#  PARSER DE TURNOS
# ----------------------------------------------------------

def parse_turno(turno_raw):
    """
    Convierte un string de turno en un par (hora_inicio, hora_fin).
    Maneja:
    - "HH:MM:SS - HH:MM:SS"
    - Cruces de medianoche
    - "Diurno/Nocturno" al final
    - "Libre" o vacío
    """
    if pd.isna(turno_raw):
        return None

    turno_raw = str(turno_raw).strip()

    if turno_raw.lower() == "libre" or turno_raw == "":
        return None

    try:
        partes = turno_raw.split("-")
        h_ini = partes[0].strip().split(" ")[0]
        h_fin = partes[1].strip().split(" ")[0]

        hora_ini = datetime.strptime(h_ini, "%H:%M:%S").time()
        hora_fin = datetime.strptime(h_fin, "%H:%M:%S").time()

        return (hora_ini, hora_fin)

    except:
        return None


# ----------------------------------------------------------
#  CARGAR TURNOS DE TU EXCEL REAL
# ----------------------------------------------------------

def load_turnos(df):
    """
    Convierte tu archivo real (3 filas de encabezado) en un diccionario:
    turnos[coordinador][dia_semana] = (inicio, fin)
    """

    # 1) Usar fila 3 como encabezado real
    df.columns = df.iloc[2]

    # 2) Eliminar filas 0,1,2
    df = df.iloc[3:].reset_index(drop=True)

    # 3) Detectar columna nombre (“Nombre”)
    col_nombre = [c for c in df.columns if "nombre" in str(c).lower()]
    if not col_nombre:
        raise KeyError("No se encontró una columna llamada 'Nombre'.")
    col_nombre = col_nombre[0]

    # 4) Detectar columnas de días
    columnas_dias = [c for c in df.columns if c != col_nombre]

    # 5) Crear estructura final
    turnos = {}

    for _, row in df.iterrows():
        persona = row[col_nombre]
        turnos[persona] = {}

        for idx, col in enumerate(columnas_dias):
            raw = row[col]
            parsed = parse_turno(raw)
            turnos[persona][idx] = parsed  # idx es día de semana relativo

    return turnos


# ----------------------------------------------------------
#  DETERMINAR SI HORA ESTÁ EN UN INTERVALO
# ----------------------------------------------------------

def hora_en_intervalo(h, h_ini, h_fin):
    if h_ini <= h_fin:
        return h_ini <= h <= h_fin
    return h >= h_ini or h <= h_fin  # cruzó medianoche


# ----------------------------------------------------------
#  ASIGNACIÓN DE VENTAS
# ----------------------------------------------------------

def asignar_ventas(df_ventas, turnos, fecha_inicio, fecha_fin, franjas):

    df = df_ventas.copy()
    df["createdAt_local"] = pd.to_datetime(df["createdAt_local"])

    # Filtro de fechas
    df = df[(df["createdAt_local"] >= fecha_inicio) & (df["createdAt_local"] <= fecha_fin)]

    if df.empty:
        return None, None, None, None

    df["dia_semana"] = df["createdAt_local"].dt.dayofweek  # 0=Lunes
    df["hora"] = df["createdAt_local"].dt.time

    registros = []

    # Ventas una a una
    for _, row in df.iterrows():
        dia = row["dia_semana"]
        hora = row["hora"]
        monto = row["qt_price_local"]

        activos = []

        for persona, dias in turnos.items():
            turno = dias.get(dia)
            if turno is None:
                continue
            ini, fin = turno
            if ini and hora_en_intervalo(hora, ini, fin):
                activos.append(persona)

        # asignación proporcional
        if activos:
            pago = monto / len(activos)
            for p in activos:
                registros.append({
                    "fecha": row["createdAt_local"].date(),
                    "hora": hora,
                    "coordinador": p,
                    "venta_original": monto,
                    "coordinadores_activos": len(activos),
                    "venta_asignada": pago
                })
        else:
            registros.append({
                "fecha": row["createdAt_local"].date(),
                "hora": hora,
                "coordinador": None,
                "venta_original": monto,
                "coordinadores_activos": 0,
                "venta_asignada": 0
            })

    df_asignado = pd.DataFrame(registros)

    # TOTALES
    df_tot = df_asignado[df_asignado["coordinador"].notna()] \
        .groupby("coordinador")["venta_asignada"].sum().reset_index()

    # FRANJAS
    def get_franja(h):
        for ini, fin in franjas:
            if hora_en_intervalo(h, ini, fin):
                return f"{ini.strftime('%H:%M')} - {fin.strftime('%H:%M')}"
        return "Fuera de rango"

    df_asignado["franja"] = df_asignado["hora"].apply(get_franja)

    df_fran = df_asignado[df_asignado["coordinador"].notna()] \
        .groupby(["coordinador", "franja"])["venta_asignada"].sum().reset_index()

    # RESUMEN GLOBAL
    total = df["qt_price_local"].sum()
    asignado = df_asignado["venta_asignada"].sum()
    no_asignado = total - asignado

    resumen = {
        "total_ventas_filtradas": float(total),
        "total_asignado": float(asignado),
        "total_sin_asignar": float(no_asignado)
    }

    return df_asignado, df_tot, df_fran, resumen

