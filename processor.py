import pandas as pd
import numpy as np
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
    - Diurno/Nocturno al final (ignorar)
    - "Libre" o vacío → None
    """
    if pd.isna(turno_raw):
        return None
    
    turno_raw = str(turno_raw).strip()

    if turno_raw.lower() == "libre" or turno_raw == "":
        return None

    # Esperado: "HH:MM:SS - HH:MM:SS ..." 
    try:
        parte = turno_raw.split(" ")[0]  # tomar solo "HH:MM:SS"
    except:
        return None

    try:
        horas = turno_raw.split("-")
        inicio = horas[0].strip().split(" ")[0]
        fin = horas[1].strip().split(" ")[0]

        h_ini = datetime.strptime(inicio, "%H:%M:%S").time()
        h_fin = datetime.strptime(fin, "%H:%M:%S").time()

        return (h_ini, h_fin)

    except:
        return None


# ----------------------------------------------------------
#  EXPANSIÓN DE TURNOS POR DÍA SEMANA
# ----------------------------------------------------------

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

def load_turnos(df_turnos):
    """
    Convierte el archivo de turnos en un diccionario:
    turnos_normalizados[coordinador][dia_semana] = (hora_inicio, hora_fin)
    """
    turnos = {}

    for _, row in df_turnos.iterrows():
        coord = row["Coordinador"]

        turnos[coord] = {}

        for idx, dia in enumerate(DIAS):
            turno_raw = row[dia]
            parsed = parse_turno(turno_raw)
            turnos[coord][idx] = parsed   # idx: 0=Lunes ... 6=Domingo

    return turnos


# ----------------------------------------------------------
#  DETERMINAR SI UNA HORA CAE EN UN INTERVALO
# ----------------------------------------------------------

def hora_en_intervalo(h, h_ini, h_fin):
    """
    Evalúa si la hora h cae en el rango [h_ini, h_fin], 
    incluyendo rangos que cruzan medianoche.
    """
    if h_ini <= h_fin:
        return h_ini <= h <= h_fin
    else:
        # Cruce de medianoche
        return h >= h_ini or h <= h_fin


# ----------------------------------------------------------
#  ASIGNACIÓN DE VENTAS
# ----------------------------------------------------------

def asignar_ventas(df_ventas, turnos, fecha_inicio, fecha_fin, franjas):
    """
    df_ventas: dataframe con createdAt_local y qt_price_local
    turnos: dict normalizado
    franjas: lista de tuplas [(h_ini, h_fin), ...]
    """

    # Filtro por fechas
    df = df_ventas.copy()
    df["createdAt_local"] = pd.to_datetime(df["createdAt_local"])

    df = df[(df["createdAt_local"] >= fecha_inicio) & (df["createdAt_local"] <= fecha_fin)]

    if df.empty:
        return None, None, None, None

    # Obtener día semana y hora
    df["dia_semana"] = df["createdAt_local"].dt.dayofweek  # 0=Lunes
    df["hora"] = df["createdAt_local"].dt.time

    registros = []

    for _, row in df.iterrows():
        dia = row["dia_semana"]
        hora = row["hora"]
        venta = row["qt_price_local"]

        activos = []

        # Ver qué coordinadores estaban activos
        for coord in turnos.keys():
            turno = turnos[coord].get(dia)

            if turno is None:
                continue

            h_ini, h_fin = turno

            if hora_en_intervalo(hora, h_ini, h_fin):
                activos.append(coord)

        # Asignación proporcional
        if len(activos) > 0:
            monto_por_coord = venta / len(activos)
            for coord in activos:
                registros.append({
                    "fecha": row["createdAt_local"].date(),
                    "hora": hora,
                    "coordinador": coord,
                    "venta_original": venta,
                    "coordinadores_activos": len(activos),
                    "venta_asignada": monto_por_coord
                })
        else:
            # Venta sin asignar
            registros.append({
                "fecha": row["createdAt_local"].date(),
                "hora": hora,
                "coordinador": None,
                "venta_original": venta,
                "coordinadores_activos": 0,
                "venta_asignada": 0
            })

    df_asignado = pd.DataFrame(registros)

    # TOTALES POR COORDINADOR
    df_totales = df_asignado[df_asignado["coordinador"].notna()].groupby("coordinador")["venta_asignada"].sum().reset_index()

    # ----------------------------------------------------------
    #  RESUMEN POR FRANJAS HORARIAS
    # ----------------------------------------------------------
    def obtener_franja(h):
        for idx, (ini, fin) in enumerate(franjas):
            if hora_en_intervalo(h, ini, fin):
                return f"{ini.strftime('%H:%M')} - {fin.strftime('%H:%M')}"
        return "Fuera de rango"

    df_asignado["franja"] = df_asignado["hora"].apply(obtener_franja)

    df_franjas = df_asignado[df_asignado["coordinador"].notna()].groupby(["coordinador", "franja"])["venta_asignada"].sum().reset_index()

    # ----------------------------------------------------------
    # TOTALES GLOBALES
    # ----------------------------------------------------------
    total_ventas = df["qt_price_local"].sum()
    asignado = df_asignado["venta_asignada"].sum()
    sin_asignar = total_ventas - asignado

    resumen_global = {
        "total_ventas_filtradas": total_ventas,
        "total_asignado": asignado,
        "total_sin_asignar": sin_asignar
    }

    return df_asignado, df_totales, df_franjas, resumen_global
