# SolarBI – Pipeline de telemetría solar

**Integrantes:** Sebastian Pineda Alvarez, Esneyder Briñez Gomez

## Descripción
Pipeline ETL con arquitectura medallón (Bronze, Silver, Gold) sobre telemetría
de inversores solares, con carga en PostgreSQL y tableros en Power BI y Grafana.

## Reproducir
1. Instalar dependencias: `pip install pandas psycopg2-binary`
2. Crear la base: `CREATE DATABASE energia_solar;`
3. Definir variables de entorno (PowerShell):
   $env:PGHOST="localhost"; $env:PGPORT="5432"; $env:PGDATABASE="energia_solar"
   $env:PGUSER="postgres"; $env:PGPASSWORD="<su_contraseña>"
4. Generar datos Bronze: `python etl/simulador.py`
5. Ejecutar el ETL: `python etl/run_etl.py`
6. Importar `grafana/dashboard_energia_solar.json` en Grafana y abrir `powerbi/*.pbix`.

## Programación diaria
Cron: `0 0 * * * cd /ruta/proyecto && python etl/run_etl.py`

## Quién hizo qué
| Integrante | Tareas |
| --- | --- |
| Sebastian Pineda Alvarez | Parte B Paso 1, 2, 3 - Parte C  |
| Esneyder Briñez Gomez | Parte A - Parte B Paso 4, 5  |