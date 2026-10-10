import os
import json
import hashlib
import pandas as pd

# ==================================================
# CONFIGURACION
# ==================================================

ARCHIVO_BRONZE = "data/bronze/telemetria.csv"
CARPETA_SILVER = "data/silver"

ARCHIVO_SILVER = os.path.join(
    CARPETA_SILVER, "telemetria_limpia.csv"
)
ARCHIVO_RECHAZADOS = os.path.join(
    CARPETA_SILVER, "telemetria_rechazada.csv"
)
ARCHIVO_REPORTE = os.path.join(
    CARPETA_SILVER, "reporte_calidad.json"
)

TAMANO_BLOQUE = 100_000

COLUMNAS = [
    "ts",
    "dispositivo_id",
    "p_ac_kw",
    "irradiancia_wm2",
    "temp_modulo_c",
]

# Limites fisicos y operativos adoptados para este ejercicio.
# Deben documentarse como reglas del contrato de datos.
LIMITES = {
    "p_ac_kw": (0, 5),
    "irradiancia_wm2": (0, 1000),
    "temp_modulo_c": (-40, 100),
}

os.makedirs(CARPETA_SILVER, exist_ok=True)

# ==================================================
# CONTADORES
# ==================================================

leidas = 0
rechazadas_faltantes = 0
rechazadas_rango = 0
rechazadas_duplicados = 0
validas = 0

# Guarda hashes de filas para detectar duplicados
# incluso entre bloques diferentes.
hashes_vistos = set()

# ==================================================
# PROCESAMIENTO POR BLOQUES
# ==================================================

primera_salida_silver = True
primera_salida_rechazados = True

for bloque in pd.read_csv(
    ARCHIVO_BRONZE,
    chunksize=TAMANO_BLOQUE,
    dtype=str,
    keep_default_na=True
):
    leidas += len(bloque)

    # Comprobar que existan las columnas esperadas
    faltan_columnas = set(COLUMNAS) - set(bloque.columns)
    if faltan_columnas:
        raise ValueError(
            f"Faltan columnas en Bronze: {faltan_columnas}"
        )

    # Normalizar vacios para la validacion.
    # Esto no modifica el archivo Bronze.
    for columna in COLUMNAS:
        bloque[columna] = bloque[columna].replace(
            r"^\s*$", pd.NA, regex=True
        )

    # Regla 1: campos obligatorios faltantes
    faltantes = bloque[COLUMNAS].isna().any(axis=1)

    # Validar tipos numericos
    for columna in LIMITES:
        bloque[columna] = pd.to_numeric(
            bloque[columna], errors="coerce"
        )

    # Un dato no numerico tambien se considera invalido
    numericos_invalidos = bloque[
        list(LIMITES)
    ].isna().any(axis=1)

    faltantes = faltantes | numericos_invalidos

    rechazados_f = bloque.loc[faltantes].copy()
    rechazados_f["motivo_rechazo"] = "datos_faltantes"
    rechazadas_faltantes += int(faltantes.sum())

    # Regla 2: rangos fisicos
    fuera_rango = pd.Series(False, index=bloque.index)

    for columna, (minimo, maximo) in LIMITES.items():
        fuera_rango |= (
            (bloque[columna] < minimo)
            | (bloque[columna] > maximo)
        )

    # Solo evaluar rango en filas no rechazadas antes
    mascara_rango = (~faltantes) & fuera_rango

    rechazados_r = bloque.loc[mascara_rango].copy()
    rechazados_r["motivo_rechazo"] = "rango_fisico"
    rechazadas_rango += int(mascara_rango.sum())

    # Regla 3: duplicados exactos de las cinco columnas
    # Los valores se convierten a texto para generar hashes.
    # Los duplicados se buscan tambien entre bloques.
    hashes = pd.util.hash_pandas_object(
        bloque[COLUMNAS].astype("string"),
        index=False
    ).astype("uint64")

    duplicado = pd.Series(False, index=bloque.index)

    for idx, valor_hash in hashes.items():
        h = int(valor_hash)

        if h in hashes_vistos:
            duplicado.at[idx] = True
        else:
            hashes_vistos.add(h)

    # Evitar contar dos veces una fila ya rechazada
    mascara_dup = (
        (~faltantes)
        & (~fuera_rango)
        & duplicado
    )

    rechazados_d = bloque.loc[mascara_dup].copy()
    rechazados_d["motivo_rechazo"] = "duplicado"
    rechazadas_duplicados += int(mascara_dup.sum())

    # Guardar filas rechazadas de este bloque
    rechazados = pd.concat(
        [rechazados_f, rechazados_r, rechazados_d],
        ignore_index=True
    )

    if not rechazados.empty:
        rechazados.to_csv(
            ARCHIVO_RECHAZADOS,
            mode="w" if primera_salida_rechazados else "a",
            header=primera_salida_rechazados,
            index=False
        )
        primera_salida_rechazados = False

    # Conservar solo las filas que pasan las tres reglas
    mascara_valida = (
        (~faltantes)
        & (~fuera_rango)
        & (~duplicado)
    )

    limpias = bloque.loc[mascara_valida, COLUMNAS].copy()

    limpias.to_csv(
        ARCHIVO_SILVER,
        mode="w" if primera_salida_silver else "a",
        header=primera_salida_silver,
        index=False
    )
    primera_salida_silver = False

    validas += len(limpias)

    print(
        f"Leidas: {leidas:,} | "
        f"Validas: {validas:,} | "
        f"Rechazadas: {leidas - validas:,}"
    )

# ==================================================
# REPORTE FINAL
# ==================================================

porcentaje_validos = (
    validas / leidas * 100 if leidas else 0
)

reporte = {
    "archivo_origen": ARCHIVO_BRONZE,
    "archivo_silver": ARCHIVO_SILVER,
    "filas_leidas": leidas,
    "rechazadas_por_datos_faltantes": rechazadas_faltantes,
    "rechazadas_por_rango_fisico": rechazadas_rango,
    "rechazadas_por_duplicados": rechazadas_duplicados,
    "filas_validas": validas,
    "filas_rechazadas_totales": leidas - validas,
    "porcentaje_datos_validos": round(
        porcentaje_validos, 4
    ),
    "porcentaje_datos_rechazados": round(
        100 - porcentaje_validos, 4
    ),
    "limites_aplicados": LIMITES,
}

with open(
    ARCHIVO_REPORTE, "w", encoding="utf-8"
) as archivo:
    json.dump(
        reporte, archivo, ensure_ascii=False, indent=4
    )

print("\n========== REPORTE SILVER ==========")
print(f"Filas leidas: {leidas:,}")
print(f"Rechazadas por faltantes: {rechazadas_faltantes:,}")
print(f"Rechazadas por rango: {rechazadas_rango:,}")
print(f"Rechazadas por duplicados: {rechazadas_duplicados:,}")
print(f"Filas validas: {validas:,}")
print(f"Filas rechazadas totales: {leidas - validas:,}")
print(f"Porcentaje valido: {porcentaje_validos:.4f}%")
print(f"\nReporte guardado en: {ARCHIVO_REPORTE}")