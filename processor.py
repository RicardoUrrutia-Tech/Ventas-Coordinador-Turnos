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
    - "Diurno/Nocturno" al final (ignorar)
    - "Libre" o vacío → None
    """

    if pd.isna(turno_raw):
        return None

    turno_raw = str(turno_raw).strip()

    if turno_raw.lower() == "libre" or turno_raw == "":
        return None

    # Esperado: "HH:MM:SS - HH:MM:SS ..."
    try:
        partes = turno_raw.split("-")
        inicio = partes[0].strip().split(" ")[0]
        fin = partes[1].strip().split(" ")[0]

        h_ini = datetime.strptime(inicio, "%H:%M:%S").time()
        h_fin = datetime.strptime(fin, "%H:%M:%S").time()

        return (h_ini, h_fin)

    except Exception:
        return None


# ----------------------------------------------------------
#  EXPANSIÓN DE TURNOS POR DÍA DE LA SEMANA
# ----------------------------------------------------------

DIAS = [
    "Lunes", "Martes", "Miércoles",
    "Jueves", "Viernes", "Sábado", "Domingo"
]


def load_turnos(df_turnos):
    """
    Convierte el archivo de turnos en un diccionario:
    turnos_normalizados[coordinador][dia_semana] = (hora_inicio, hora_fin)

    Detecta automáticamente la columna donde vienen los nombres.
    """

    # --------------------------------------------
    # 1. Detectar columna de nombre del coordinador
    # --------------------------------------------
    posibles_nombres = ["coordinador", "nombre", "ejecutivo", "agente", "usuario"]

    col_coord = None
    for col in df_turnos.columns:
        if any(p in col.lower() for p in posibles_nombres):
            col_coord = col
            break

    if col_coord is None:
        raise KeyError(
            "No se encontró columna de nombre/coordinador en el archivo de turnos. "
            "Asegúrate de que exista una columna como 'Nombre' o 'Coordinador'."
        )

    turnos = {}

    # --------------------------------------------
    # 2. Leer fila por fila (coordinador por coordinador)
    # --------------------------------------------
    for _, row in df_turnos.iterrows():

        coord = str(row[col_coord]).strip()
        turnos[coord] = {}

        # Día de la semana: 0=Lunes ... 6=Domingo
        # El archivo puede traer nombres repetidos en dos semanas,
        # aquí normalizamos tomando solo el *día de la semana*.

        for idx, dia in enumerate(DIAS):
            # Buscar columnas que contengan ese día (ej: "lunes 03-nov")
            columnas_dia = [c for c in df_turnos.columns if dia.lower() in c.lower()]

            if len(columnas_dia) == 0:
                turnos[coord][idx] = None
                continue

            # Si hay más de una semana, tomamos todas y priorizamos el último valor no vacío
            valor = None
            for col_d in columnas_dia:
                candidato = row[col_d]
                if pd.notna(candidato) and str(candidato).strip().lower() != "libre":
                    valor = candidato  # nos quedamos con el turno válido más reciente

            parsed = parse_turno(valor)
            turnos[coord][idx] = parsed

    return turnos


# ----------------------------------------------------------
#  DETERMINAR SI UNA HORA CAE EN UN INTERVALO
# ----------------------------------------------------------

def hora_en_intervalo(h, h_ini, h_fin):
    """
    Evalúa si la hora h cae en el rango [h_ini, h_fin].
    Maneja rangos normales y rangos que cruzan medianoche.
    """
    if h_ini <= h_fin:
        # Caso normal
        return h_ini <= h <= h_fin
    else:
        # Cruce de medianoche (ej: 13:00 → 00:00)
        return h >= h_ini or h <= h_fin


# ----------------------------------------------------------
#  ASIGNACIÓN DE VENTAS
# ----------------------------------------------------------

def asignar_ventas(df_ventas, turnos, fecha_inicio, fecha_fin, franjas):
    """
    Asigna proporcionalmente las ventas a los coordinadores activos.
    df_ventas debe incluir:
    - createdAt_local (datetime)
    - qt_price_local (monto)

    franjas = lista de tuplas de time: [(h_ini, h_fin), ...]
    """

    # --------------------------------------------
    # 1. Filtrar ventas por rango de fechas
    # --------------------------------------------
    df = df_ventas.copy()
    df["createdAt_local"] = pd.to_datetime(df["createdAt_local"])

    df = df[(df["createdAt_local"] >= fecha_inicio) & (df["createdAt_local"] <= fecha_fin)]

    if df.empty:
        return None, None, None, None

    # --------------------------------------------
    # 2. Extraer día de semana y hora
    # --------------------------------------------
    df["dia_semana"] = df["createdAt_local"].dt.dayofweek  # 0=Lunes
    df["hora"] = df["createdAt_local"].dt.time

    registros = []

    # --------------------------------------------
    # 3. Evaluar venta por venta
    # --------------------------------------------
    for _, row in df.iterrows():
        dia = row["dia_semana"]
        hora = row["hora"]
        venta = row["qt_price_local"]

        activos = []

        # Determinar qué coordinadores estaban activos
        for coord, turnos_coord in turnos.items():
            turno = turnos_coord.get(dia)

            if turno is None:
                continue

            h_ini, h_fin = turno

            if hora_en_intervalo(hora, h_ini, h_fin):
                activos.append(coord)

        # Asignación proporcional
        if len(activos) > 0:
            monto_x_coord = venta / len(activos)
            for coord in activos:
                registros.append({
                    "fecha": row["createdAt_local"].date(),
                    "hora": hora,
                    "coordinador": coord,
                    "venta_original": venta,
                    "coordinadores_activos": len(activos),
                    "venta_asignada": monto_x_coord
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

    # --------------------------------------------
    # 4. Totales por coordinador
    # --------------------------------------------
    df_totales = (
        df_asignado[df_asignado["coordinador"].notna()]
        .groupby("coordinador")["venta_asignada"]
        .sum()
        .reset_index()
    )

    # --------------------------------------------
    # 5. Franjas horarias
    # --------------------------------------------
    def obtener_franja(h):
        for ini, fin in franjas:
            if hora_en_intervalo(h, ini, fin):
                return f"{ini.strftime('%H:%M')} - {fin.strftime('%H:%M')}"
        return "Fuera de rango"

    df_asignado["franja"] = df_asignado["hora"].apply(obtener_franja)

    df_franjas = (
        df_asignado[df_asignado["coordinador"].notna()]
        .groupby(["coordinador", "franja"])["venta_asignada"]
        .sum()
        .reset_index()
    )

    # --------------------------------------------
    # 6. Resumen global
    # --------------------------------------------
    total_ventas = df["qt_price_local"].sum()
    asignado = df_asignado["venta_asignada"].sum()
    sin_asignar = total_ventas - asignado

    resumen_global = {
        "total_ventas_filtradas": float(total_ventas),
        "total_asignado": float(asignado),
        "total_sin_asignar": float(sin_asignar)
    }

    return df_asignado, df_totales, df_franjas, resumen_global

