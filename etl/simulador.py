import csv
import math
import os
import random
from datetime import datetime, timedelta

# ==================================================
# CONFIGURACION
# ==================================================

TOTAL_REGISTROS = 4_000_000
REGISTROS_POR_DIA = 288
DIAS = 3
REGISTROS_POR_DISPOSITIVO = DIAS * REGISTROS_POR_DIA

POTENCIA_KWP = 5.0
INTERVALO_MIN = 5
SEMILLA = 42

random.seed(SEMILLA)

INICIO = datetime(2026, 10, 5, 0, 0)

ARCHIVO = "data/bronze/telemetria.csv"
os.makedirs(os.path.dirname(ARCHIVO), exist_ok=True)

# Numero de dispositivos virtuales necesarios
NUM_DISPOSITIVOS = math.ceil(
    TOTAL_REGISTROS / REGISTROS_POR_DISPOSITIVO
)

# ==================================================
# GENERACION DE BRONZE
# No se transforman ni corrigen los datos
# ==================================================

def generar_fila(indice):
    dispositivo_num = indice // REGISTROS_POR_DISPOSITIVO
    posicion = indice % REGISTROS_POR_DISPOSITIVO

    dispositivo_id = f"INV-{dispositivo_num + 1:05d}"

    ts = INICIO + timedelta(
        minutes=INTERVALO_MIN * posicion
    )

    hora = ts.hour + ts.minute / 60

    sol = max(
        0.0,
        math.sin(math.pi * (hora - 6) / 12)
    )

    irradiancia = round(
        1000 * sol * random.uniform(0.7, 1.0),
        1
    )

    p_ac = round(
        POTENCIA_KWP
        * irradiancia / 1000
        * random.uniform(0.80, 0.90),
        3
    )

    temp_modulo = round(
        22 + 30 * sol + random.uniform(-2, 2),
        1
    )

    fila = [
        ts.isoformat(sep=" "),
        dispositivo_id,
        p_ac,
        irradiancia,
        temp_modulo
    ]

    # Anomalias de acuerdo con el simulador del curso
    r = random.random()

    if r < 0.02:
        # Potencia negativa
        fila[2] = -1

    elif r < 0.04:
        # Dato faltante: irradiancia vacia
        fila[3] = ""

    return fila, r


def main():
    filas_escritas = 0
    anomalas_negativas = 0
    datos_faltantes = 0
    filas_duplicadas = 0
    fila_anterior = None

    with open(
        ARCHIVO,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        w = csv.writer(f)

        w.writerow([
            "ts",
            "dispositivo_id",
            "p_ac_kw",
            "irradiancia_wm2",
            "temp_modulo_c"
        ])

        for i in range(TOTAL_REGISTROS):
            fila, r = generar_fila(i)

            if r < 0.02:
                anomalas_negativas += 1
            elif r < 0.04:
                datos_faltantes += 1

            # La fila duplicada ocupa una de las
            # 4 millones de posiciones del dataset.
            if r > 0.98 and fila_anterior is not None:
                fila = fila_anterior.copy()
                filas_duplicadas += 1

            w.writerow(fila)
            filas_escritas += 1

            fila_anterior = fila.copy()

            if filas_escritas % 500_000 == 0:
                print(
                    f"Progreso: {filas_escritas:,} "
                    f"/ {TOTAL_REGISTROS:,}"
                )

    print("\nGeneracion finalizada")
    print(f"Archivo: {ARCHIVO}")
    print(f"Registros: {filas_escritas:,}")
    print(f"Dispositivos virtuales: {NUM_DISPOSITIVOS:,}")
    print(f"Potencia nominal: {POTENCIA_KWP} kWp")
    print(f"Anomalias negativas: {anomalas_negativas:,}")
    print(f"Datos faltantes: {datos_faltantes:,}")
    print(f"Filas duplicadas: {filas_duplicadas:,}")


if __name__ == "__main__":
    main()