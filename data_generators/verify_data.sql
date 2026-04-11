-- =============================================
-- Maritime Lakehouse Platform
-- Script de verification des donnees
-- A executer dans SSMS apres le generateur
-- =============================================

USE MaritimeDB;
GO

-- Compter les lignes par table
SELECT 'vessel_classes'   AS table_name, COUNT(*) AS row_count FROM vessel_classes UNION ALL
SELECT 'vessels',                         COUNT(*) FROM vessels          UNION ALL
SELECT 'ports',                           COUNT(*) FROM ports            UNION ALL
SELECT 'terminals',                       COUNT(*) FROM terminals        UNION ALL
SELECT 'berths',                          COUNT(*) FROM berths           UNION ALL
SELECT 'voyages',                         COUNT(*) FROM voyages          UNION ALL
SELECT 'port_calls',                      COUNT(*) FROM port_calls       UNION ALL
SELECT 'cargo_types',                     COUNT(*) FROM cargo_types      UNION ALL
SELECT 'cargo_orders',                    COUNT(*) FROM cargo_orders     UNION ALL
SELECT 'cargo_manifests',                 COUNT(*) FROM cargo_manifests  UNION ALL
SELECT 'clients',                         COUNT(*) FROM clients          UNION ALL
SELECT 'contracts',                       COUNT(*) FROM contracts        UNION ALL
SELECT 'seafarers',                       COUNT(*) FROM seafarers        UNION ALL
SELECT 'crew_assignments',                COUNT(*) FROM crew_assignments  UNION ALL
SELECT 'fuel_grades',                     COUNT(*) FROM fuel_grades      UNION ALL
SELECT 'bunkering_events',                COUNT(*) FROM bunkering_events
ORDER BY table_name;
GO

-- Apercu des navires
SELECT TOP 5
    v.vessel_name,
    vc.class_name,
    vc.vessel_type,
    v.flag_country,
    v.build_year,
    v.deadweight_tons
FROM vessels v
JOIN vessel_classes vc ON v.class_id = vc.class_id;
GO

-- Apercu des voyages
SELECT TOP 5
    voyage_code,
    voyage_status,
    distance_nm,
    etd,
    eta,
    DATEDIFF(day, etd, eta) AS duration_days
FROM voyages
ORDER BY etd DESC;
GO

-- Apercu des ports
SELECT
    port_name,
    country,
    region,
    port_type
FROM ports
ORDER BY region, country;
GO

-- Statistiques globales
SELECT
    (SELECT COUNT(*) FROM voyages WHERE voyage_status = 'Completed') AS completed_voyages,
    (SELECT COUNT(*) FROM voyages WHERE voyage_status = 'In Progress') AS in_progress_voyages,
    (SELECT COUNT(*) FROM voyages WHERE voyage_status = 'Planned') AS planned_voyages,
    (SELECT COUNT(*) FROM cargo_orders WHERE order_status = 'Delivered') AS delivered_orders,
    (SELECT SUM(total_cost_usd) FROM bunkering_events) AS total_fuel_cost_usd;
GO
