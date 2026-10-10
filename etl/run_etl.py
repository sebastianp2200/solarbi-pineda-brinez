import os
import sys
import subprocess
from pathlib import Path

import psycopg2


# =====================================================
# CONFIGURACION
# =====================================================

ROOT = Path(__file__).resolve().parent.parent

SCRIPT_SILVER = ROOT / "etl" / "silver.py"
ARCHIVO_SILVER = ROOT / "data" / "silver" / "telemetria_limpia.csv"

BLOQUE_COPY = 100_000


def conectar():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "energia_solar"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.environ["PGPASSWORD"],
    )


# =====================================================
# 1. EJECUTAR BRONZE -> SILVER
# =====================================================

def ejecutar_silver():
    print("\n[1/4] Ejecutando validacion Silver...")

    subprocess.run(
        [sys.executable, str(SCRIPT_SILVER)],
        cwd=str(ROOT),
        check=True,
    )

    if not ARCHIVO_SILVER.exists():
        raise FileNotFoundError(
            f"No se genero el archivo: {ARCHIVO_SILVER}"
        )


# =====================================================
# 2. CREAR TABLAS
# =====================================================

def crear_tablas(cur):
    cur.execute("""
        CREATE SCHEMA IF NOT EXISTS silver;

        CREATE SCHEMA IF NOT EXISTS dwh;

        CREATE TABLE IF NOT EXISTS silver.lectura_5min (
            ts TIMESTAMP NOT NULL,
            dispositivo_id TEXT NOT NULL,
            p_ac_kw DOUBLE PRECISION NOT NULL,
            irradiancia_wm2 DOUBLE PRECISION NOT NULL,
            temp_modulo_c DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (ts, dispositivo_id)
        );

        CREATE TABLE IF NOT EXISTS dwh.fact_energia_dia (
            fecha DATE NOT NULL,
            dispositivo TEXT NOT NULL,
            energia_kwh DOUBLE PRECISION NOT NULL,
            pct_datos_validos DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (fecha, dispositivo)
        );
    """)


# =====================================================
# 3. CARGAR LECTURAS SILVER
# =====================================================

def cargar_lecturas(cur):
    print("\n[2/4] Cargando lecturas de 5 minutos...")

    # Reconstruir los datos derivados desde Silver.
    cur.execute("""
        TRUNCATE TABLE
            dwh.fact_energia_dia,
            silver.lectura_5min;
    """)

    # COPY es adecuado para cargas grandes de CSV.
    with open(
        ARCHIVO_SILVER,
        "r",
        encoding="utf-8",
        newline=""
    ) as archivo:
        cur.copy_expert("""
            COPY silver.lectura_5min (
                ts,
                dispositivo_id,
                p_ac_kw,
                irradiancia_wm2,
                temp_modulo_c
            )
            FROM STDIN
            WITH (
                FORMAT CSV,
                HEADER TRUE,
                NULL ''
            );
        """, archivo)

    cur.execute("""
        SELECT COUNT(*)
        FROM silver.lectura_5min;
    """)

    cantidad = cur.fetchone()[0]
    print(f"Lecturas cargadas: {cantidad:,}")


# =====================================================
# 4. RESUMEN DIARIO DE ENERGIA
# =====================================================

def construir_gold(cur):
    print("\n[3/4] Calculando energia diaria...")

    cur.execute("""
        INSERT INTO dwh.fact_energia_dia (
            fecha,
            dispositivo,
            energia_kwh,
            pct_datos_validos
        )
        SELECT
            ts::date AS fecha,
            dispositivo_id AS dispositivo,

            -- Energia = potencia media de cada intervalo
            -- por 5/60 horas. Se suman los intervalos.
            SUM(p_ac_kw * (5.0 / 60.0)) AS energia_kwh,

            -- Porcentaje respecto a 288 intervalos diarios.
            LEAST(
                100.0,
                COUNT(*) * 100.0 / 288.0
            ) AS pct_datos_validos

        FROM silver.lectura_5min

        GROUP BY
            ts::date,
            dispositivo_id;
    """)

    cur.execute("""
        SELECT COUNT(*)
        FROM dwh.fact_energia_dia;
    """)

    cantidad = cur.fetchone()[0]
    print(f"Resúmenes diarios generados: {cantidad:,}")


# =====================================================
# 5. CONTEOS Y EJECUCION TRANSACCIONAL
# =====================================================

def ejecutar_carga():
    print("\nConectando a PostgreSQL...")

    conexion = conectar()

    try:
        with conexion:
            with conexion.cursor() as cur:
                crear_tablas(cur)
                cargar_lecturas(cur)
                construir_gold(cur)

                cur.execute("""
                    SELECT COUNT(*)
                    FROM silver.lectura_5min;
                """)
                lecturas = cur.fetchone()[0]

                cur.execute("""
                    SELECT COUNT(*)
                    FROM dwh.fact_energia_dia;
                """)
                resumenes = cur.fetchone()[0]

                print("\n[4/4] Carga completada")
                print(f"Total Silver: {lecturas:,}")
                print(f"Total Gold: {resumenes:,}")

    finally:
        conexion.close()


def main():
    ejecutar_silver()
    ejecutar_carga()

    print("\nETL finalizado correctamente.")


if __name__ == "__main__":
    main()