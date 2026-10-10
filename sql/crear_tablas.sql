-- Esquemas
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS dwh;

-- Capa Silver: lecturas limpias de 5 minutos
CREATE TABLE IF NOT EXISTS silver.lectura_5min (
    ts TIMESTAMP NOT NULL,
    dispositivo_id TEXT NOT NULL,
    p_ac_kw DOUBLE PRECISION NOT NULL,
    irradiancia_wm2 DOUBLE PRECISION NOT NULL,
    temp_modulo_c DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (ts, dispositivo_id)
);

-- Capa Gold: energía diaria por dispositivo
CREATE TABLE IF NOT EXISTS dwh.fact_energia_dia (
    fecha DATE NOT NULL,
    dispositivo TEXT NOT NULL,
    energia_kwh DOUBLE PRECISION NOT NULL,
    pct_datos_validos DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (fecha, dispositivo)
);