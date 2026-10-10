SELECT COUNT(*) AS total_silver FROM silver.lectura_5min;
SELECT COUNT(*) AS total_gold FROM dwh.fact_energia_dia;

SELECT fecha, dispositivo, energia_kwh, pct_datos_validos
FROM dwh.fact_energia_dia
ORDER BY fecha, dispositivo
LIMIT 20;