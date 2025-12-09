import pandas as pd
from datetime import datetime, time

# =======================================================
# 🔍 FUNCIÓN DE DIAGNÓSTICO (OPCIONAL)
# =======================================================

def diagnosticar_turnos(file):
    """
    Devuelve múltiples lecturas del archivo para inspección en app.py.
    No afecta el procesamiento real.
    """
    resultados = {}

    # Lectura RAW
    try:
        df_raw = pd.read_excel(file, header=None)
        resultados["RAW"] = df_raw
    except Exception as e:
        resultados["RAW"] = f"Error RAW: {e}"

    # Lecturas con distintos headers
    for h in [0, 1, 2, 3, 4]:
        try:
            dfh = pd.read_excel(file, header=h)
            resultados[f"header_{h}"] = dfh
        except Exception as e:
            resultados[f"header_{h}"] = f"Error: {e}"

    return resultados


# =======================================================
# 🔧 PARSER DE TURNOS
# =======================================================

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


# =======================================================
# 🔧 CARGA DE TURNOS (SE AJUSTARÁ UNA VEZ QUE VEAMOS EL DIAG)
# =======================================================

def load_turnos(df):
    """
    Esta versión es provisional hasta que veamos cómo Pandas interpreta tu archivo.
    """
    raise Exception("⚠️ El processor final se generará después del diagnóstico.")


# =======================================================
# 🔧 FUNCIÓN AUXILIAR
# =======================================================

def hora_en_intervalo(h, h_ini, h_fin):
    if h_ini <= h_fin:
        return h_ini <= h <= h_fin
    return h >= h_ini or h <= h_fin


# =======================================================
# 🔧 ASIGNACIÓN DE VENTAS (SE MANTIENE IGUAL)
# =======================================================

def asignar_ventas(df_ventas, turnos, fecha_inicio, fecha_fin, franjas):

    df = df_ventas.copy()
    df["createdAt_local"] = pd.to_datetime(df["createdAt_local"])

    df = df[(df["createdAt_local"] >= fecha_inicio) & (df["createdAt_local"] <= fecha_fin)]

    if df.empty:
        return None, None, None, None

    df["dia_semana"] = df["createdAt_local"].dt.dayofweek
    df["hora"] = df["createdAt_local"].dt.time

    registros = []

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

        if activos:
            asignado = monto / len(activos)
            for p in activos:
                registros.append({
                    "fecha": row["createdAt_local"],
                    "hora": hora,
                    "coordinador": p,
                    "venta_original": monto,
                    "coordinadores_activos": len(activos),
                    "venta_asignada": asignado
                })
        else:
            registros.append({
                "fecha": row["createdAt_local"],
                "hora": hora,
                "coordinador": None,
                "venta_original": monto,
                "coordinadores_activos": 0,
                "venta_asignada": 0
            })

    df_asignado = pd.DataFrame(registros)

    df_tot = df_asignado[df_asignado["coordinador"].notna()] \
        .groupby("coordinador")["venta_asignada"].sum().reset_index()

    def obtener_franja(h):
        for ini, fin in franjas:
            if hora_en_intervalo(h, ini, fin):
                return f"{ini.strftime('%H:%M')} - {fin.strftime('%H:%M')}"
        return "Fuera de rango"

    df_asignado["franja"] = df_asignado["hora"].apply(obtener_franja)

    df_fran = df_asignado[df_asignado["coordinador"].notna()] \
        .groupby(["coordinador", "franja"])["venta_asignada"].sum().reset_index()

    resumen = {
        "ventas_filtradas": float(df["qt_price_local"].sum()),
        "total_asignado": float(df_asignado["venta_asignada"].sum()),
        "no_asignado": float(df["qt_price_local"].sum() - df_asignado["venta_asignada"].sum())
    }

    return df_asignado, df_tot, df_fran, resumen

