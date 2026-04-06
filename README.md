# Maritime Lakehouse Platform

![Architecture](https://img.shields.io/badge/Architecture-Medallion-success)
![Azure](https://img.shields.io/badge/Platform-Microsoft%20Azure-blue)
![ADF](https://img.shields.io/badge/Ingestion-Azure%20Data%20Factory%20%2B%20SHIR-purple)
![Databricks](https://img.shields.io/badge/Processing-Azure%20Databricks-red)
![ADLS](https://img.shields.io/badge/Storage-ADLS%20Gen2-orange)
![DeltaLake](https://img.shields.io/badge/Format-Delta%20Lake-success)
![CICD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-black)
![PowerBI](https://img.shields.io/badge/Serving-Power%20BI-yellow)

---

## Overview

End-to-end Azure Maritime Logistics Data Platform implementing
Medallion Architecture (Bronze → Silver → Gold) across 8 business
domains — Fleet, Navigation, Port Operations, Cargo, Telemetry,
Fuel Operations, Crewing, and Commercial.

The platform ingests data from an on-premises SQL Server instance
via Azure Data Factory with a Self-Hosted Integration Runtime (SHIR),
combines it with CSV/JSON file drops and real-time IoT streaming
via Azure Event Hubs, and processes everything through Azure
Databricks into an analytics-ready star schema served in Power BI.

---

## Technology Stack

| Layer             | Technology                             |
|-------------------|----------------------------------------|
| Source            | SQL Server local (YOUSSOUF\SQLEXPRESS) |
| Ingestion Batch   | Azure Data Factory + SHIR              |
| Ingestion Stream  | Azure Event Hubs                       |
| Storage           | Azure Data Lake Storage Gen2           |
| Processing        | Azure Databricks + Delta Lake          |
| Governance        | Unity Catalog + Azure Key Vault        |
| Monitoring        | Azure Monitor + Databricks DLM         |
| CI/CD             | GitHub Actions                         |
| Serving           | Power BI                               |

---

## Data Sources & Ingestion

| Source                        | Type            | Ingestion Tool                  | Domains Alimentés                                      |
|-------------------------------|-----------------|----------------------------------|--------------------------------------------------------|
| SQL Server local (SQLEXPRESS) | Relationnel     | ADF + SHIR + Watermark           | FLEET, NAVIGATION, PORTOPS, CARGO, CREWING, COMMERCIAL |
| CSV / JSON Files              | Fichiers plats  | ADF Copy Activity (scheduled)    | FUELOPS, WEATHER                                       |
| Azure Event Hubs              | Streaming       | Databricks Structured Streaming  | TELEMETRY (AIS positions, Engine metrics)              |

---

## End-to-End Architecture Flow
```
┌──────────────────────────────────────────────────────────────────┐
│                        SOURCE LAYER                              │
├───────────────────────┬────────────────┬─────────────────────────┤
│   SQL Server local    │  CSV / JSON    │    Python Producer       │
│   YOUSSOUF\SQLEXPRESS │  Files         │    (Event Hubs SDK)      │
│                       │                │                          │
│   Script Python       │  Générés       │    AIS positions simulées│
│   18 tables           │  localement    │    Engine metrics simulés│
│   ~70K+ lignes        │  uploadés ADLS │    150 navires actifs    │
│                       │                │                          │
│   FLEET               │  FUELOPS       │    TELEMETRY             │
│   NAVIGATION          │  WEATHER       │    ais-positions-stream  │
│   PORTOPS             │                │    engine-metrics-stream │
│   CARGO               │                │                          │
│   CREWING             │                │                          │
│   COMMERCIAL          │                │                          │
└──────────┬────────────┴───────┬────────┴────────────┬────────────┘
           │                    │                      │
           │ ADF + SHIR         │ ADF Copy Activity    │ Pas d'ADF
           │ Copy Activity      │ Scheduled trigger    │ Direct
           │ Watermark Incr.    │                      │ Streaming
           │ SHIR sur laptop    │                      │
           ▼                    ▼                      │
┌──────────────────────────────────────────────────────┼────────────┐
│                 ADLS Gen2 — Landing Zone              │            │
│                                                       │            │
│  landing/erp/fleet/vessels/                           │            │
│  landing/erp/fleet/vessel_classes/                    │            │
│  landing/erp/navigation/voyages/                      │            │
│  landing/erp/navigation/port_calls/                   │            │
│  landing/erp/portops/ports/                           │            │
│  landing/erp/portops/terminals/                       │            │
│  landing/erp/portops/berths/                          │            │
│  landing/erp/cargo/cargo_orders/                      │            │
│  landing/erp/cargo/cargo_manifests/                   │            │
│  landing/erp/crewing/seafarers/                       │            │
│  landing/erp/crewing/crew_assignments/                │            │
│  landing/erp/commercial/clients/                      │            │
│  landing/erp/commercial/contracts/                    │            │
│  landing/files/fuelops/bunkering_events/              │            │
│  landing/files/fuelops/consumption_logs/              │            │
│  landing/files/weather/reports/                       │            │
│  landing/streaming/ais/                               │            │
│  landing/streaming/telemetry/                         │            │
└──────────────────────────────────────────────────────┼────────────┘
           │                                            │
           │  Databricks Auto Loader                    │ Databricks
           │  (batch — toutes les 24h)                  │ Structured
           │                                            │ Streaming
           ▼                                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                   DATABRICKS — MEDALLION ARCHITECTURE            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BRONZE — Raw Delta Tables (schéma préservé, append only)        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ bronze_fleet     bronze_navigation    bronze_portops      │   │
│  │ bronze_cargo     bronze_telemetry     bronze_fuelops      │   │
│  │ bronze_crewing   bronze_commercial                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  SILVER — Cleaned, Validated, SCD Type 2                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ silver_fleet     silver_navigation    silver_portops      │   │
│  │ silver_cargo     silver_telemetry     silver_fuelops      │   │
│  │ silver_crewing   silver_commercial                        │   │
│  │                                                           │   │
│  │ Transformations :                                         │   │
│  │ - Schema enforcement & type harmonization                 │   │
│  │ - Duplicate removal & null validation                     │   │
│  │ - SCD Type 2 (vessels, routes, clients)                   │   │
│  │ - Delta Constraints + Quarantine tables                   │   │
│  │ - EEOI / CII calculations (fuelops)                       │   │
│  │ - Haversine distance (navigation)                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  GOLD — Star Schema Analytics (Kimball)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ FACTS                      DIMENSIONS                     │   │
│  │ fact_voyages               dim_vessel      (SCD Type 2)   │   │
│  │ fact_port_calls            dim_port                       │   │
│  │ fact_fuel_consumption      dim_date                       │   │
│  │ fact_cargo_deliveries      dim_cargo_type                 │   │
│  │ fact_vessel_telemetry      dim_client      (SCD Type 2)   │   │
│  │ fact_commercial_revenue    dim_fuel_grade                 │   │
│  │ fact_crew_assignments      dim_crew_rank                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  VIEWS — KPIs Métier                                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ v_vessel_performance     v_port_efficiency                │   │
│  │ v_fleet_environmental    v_cargo_ontime                   │   │
│  │ v_revenue_by_route       v_crew_utilization               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  OPTIMIZE & ZORDER                                               │
│  OPTIMIZE gold.fact_voyages ZORDER BY (voyage_date, vessel_id)  │
│  OPTIMIZE gold.fact_fuel_consumption ZORDER BY (log_date)       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
           │
           │  Power BI Desktop Connector
           │  (Azure Databricks — Import / DirectQuery)
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      POWER BI — SERVING                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Fleet Performance       Fuel & Environment (CII Rating A→E)    │
│  Voyage Analytics        Port Operations & Turnaround           │
│  Cargo & Revenue         Crew Dashboard                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Business Domains

| # | Domain     | Description                               | Source         | Tables Principales                          |
|---|------------|-------------------------------------------|----------------|---------------------------------------------|
| 1 | FLEET      | Vessel master data & specifications       | SQL Server     | vessels, vessel_classes, vessel_documents   |
| 2 | NAVIGATION | Voyages, routes, port calls               | SQL Server     | voyages, voyage_legs, port_calls            |
| 3 | PORTOPS    | Ports, terminals, berths                  | SQL Server     | ports, terminals, berths                    |
| 4 | CARGO      | Orders, manifests, cargo types            | SQL Server     | cargo_orders, cargo_manifests, cargo_types  |
| 5 | TELEMETRY  | AIS positions, engine metrics (streaming) | Event Hubs     | vessel_positions, engine_metrics, alerts    |
| 6 | FUELOPS    | Fuel consumption, bunkering, emissions    | CSV Files      | fuel_consumption, bunkering_events          |
| 7 | CREWING    | Seafarers, certifications, assignments    | SQL Server     | seafarers, certifications, crew_assignments |
| 8 | COMMERCIAL | Clients, contracts, freight rates         | SQL Server     | clients, contracts, freight_rates           |

---

## Dataset Scale

| Entity              | Volume         |
|---------------------|----------------|
| Vessels             | 150            |
| Ports               | 20 (mondiaux)  |
| Voyages             | ~18,000        |
| Port Calls          | ~54,000        |
| Cargo Orders        | ~25,000        |
| Cargo Manifests     | ~25,000        |
| Bunkering Events    | ~12,000        |
| Crew Assignments    | ~8,000         |
| Seafarers           | 500            |
| Contracts           | 300            |
| AIS Positions       | ~15M (stream)  |
| Engine Metrics      | ~8M (stream)   |

---

## Governance & Monitoring

| Pilier           | Outil                                   | Description                              |
|------------------|-----------------------------------------|------------------------------------------|
| Access Control   | Unity Catalog RBAC                      | Rôles par couche Bronze/Silver/Gold      |
| Secrets          | Azure Key Vault                         | Zéro credential en clair dans le code   |
| Data Quality     | Delta Constraints + Quarantine tables   | Lignes invalides tracées séparément      |
| Data Lineage     | Unity Catalog Auto-lineage              | Traçabilité source → Gold automatique    |
| Pipeline Audit   | pipeline_audit_log (table Delta custom) | Rows processed, status, duration         |
| Infra Monitoring | Azure Monitor + Log Analytics           | Alertes ADF failures, coûts             |
| Data Monitoring  | Databricks Lakehouse Monitoring (DLM)   | Data drift, distribution, anomalies     |
| Time Travel      | Delta Lake History                      | Audit trail + rollback possible          |

---

## CI/CD Pipeline
```
Developer → git push → GitHub
        │
        ▼
Pull Request → CI Workflow (ci.yml)
  ├── Linting          : flake8, black
  ├── Type checking    : mypy
  ├── Unit tests       : pytest + PySpark local
  ├── Validate ADF     : JSON schema validation
  └── Validate Jobs    : Databricks job configs
        │
        ▼
Merge → main → CD Workflows
  ├── cd_databricks.yml
  │   ├── Deploy notebooks  → Databricks workspace
  │   └── Deploy jobs       → Databricks workflows
  └── cd_adf.yml
      └── Deploy pipelines  → Azure Data Factory
```

---

## Cost Management

| Service             | Tier               | Cost/month |
|---------------------|--------------------|------------|
| SQL Server local    | SQLEXPRESS (free)  | $0         |
| ADLS Gen2           | LRS ~50GB          | ~$2        |
| Azure Data Factory  | ~20 runs/day + SHIR| ~$3        |
| Azure Databricks    | 4h/day DS3_v2      | ~$15       |
| Azure Event Hubs    | Basic 1 TU         | ~$10       |
| Azure Key Vault     | Standard           | ~$0.5      |
| Azure Monitor       | Basic logs         | ~$2        |
| Power BI            | Free Desktop       | $0         |
| **Total**           |                    | **~$32.5/month** |

> Budget alert configuré à $80 sur rg-maritime-lakehouse-dev
> Databricks cluster : auto-terminate après 30 min d'inactivité
> Azure for Students : $100 crédit → ~3 mois de projet

---

## Repository Structure
```
maritime-lakehouse-platform/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                    ← Tests + validation PR
│       ├── cd_databricks.yml         ← Deploy notebooks + jobs
│       └── cd_adf.yml                ← Deploy ADF pipelines
│
├── databricks/
│   ├── bronze/                       ← Raw ingestion notebooks
│   │   ├── bronze_fleet.ipynb
│   │   ├── bronze_navigation.ipynb
│   │   ├── bronze_portops.ipynb
│   │   ├── bronze_cargo.ipynb
│   │   ├── bronze_telemetry.ipynb
│   │   ├── bronze_fuelops.ipynb
│   │   ├── bronze_crewing.ipynb
│   │   └── bronze_commercial.ipynb
│   ├── silver/                       ← Transformation notebooks
│   │   ├── silver_fleet.ipynb
│   │   ├── silver_navigation.ipynb
│   │   ├── silver_portops.ipynb
│   │   ├── silver_cargo.ipynb
│   │   ├── silver_telemetry.ipynb
│   │   ├── silver_fuelops.ipynb
│   │   ├── silver_crewing.ipynb
│   │   └── silver_commercial.ipynb
│   ├── gold/                         ← Star schema notebooks
│   │   ├── gold_dim_vessel.ipynb
│   │   ├── gold_dim_port.ipynb
│   │   ├── gold_dim_date.ipynb
│   │   ├── gold_dim_cargo_type.ipynb
│   │   ├── gold_dim_client.ipynb
│   │   ├── gold_dim_fuel_grade.ipynb
│   │   ├── gold_fact_voyages.ipynb
│   │   ├── gold_fact_port_calls.ipynb
│   │   ├── gold_fact_fuel_consumption.ipynb
│   │   ├── gold_fact_cargo_deliveries.ipynb
│   │   └── gold_fact_commercial_revenue.ipynb
│   ├── views/                        ← KPI views notebooks
│   │   ├── v_vessel_performance.ipynb
│   │   ├── v_fleet_environmental.ipynb
│   │   ├── v_port_efficiency.ipynb
│   │   ├── v_cargo_ontime.ipynb
│   │   ├── v_revenue_by_route.ipynb
│   │   └── v_crew_utilization.ipynb
│   ├── jobs/                         ← Databricks workflow JSON
│   │   ├── maritime_etl_pipeline.json
│   │   └── optimize_gold_tables.json
│   ├── config.ipynb                  ← Variables globales
│   ├── init_lakehouse.ipynb          ← Unity Catalog setup
│   └── optimize_gold_tables.ipynb   ← OPTIMIZE + ZORDER
│
├── adf/
│   ├── pipeline/                     ← ADF pipeline JSON
│   ├── dataset/                      ← ADF dataset JSON
│   └── linkedService/                ← ADF linked service JSON
│
├── data_generators/                  ← Scripts génération données
│   ├── generate_maritime_data.py     ← SQL Server population
│   ├── generate_fuelops_csv.py       ← CSV FUELOPS
│   ├── generate_weather_json.py      ← JSON WEATHER
│   ├── producer_ais.py               ← Event Hubs AIS stream
│   └── producer_engine_metrics.py    ← Event Hubs IoT stream
│
├── tests/
│   ├── unit/                         ← PySpark unit tests
│   │   ├── test_silver_fleet.py
│   │   ├── test_silver_navigation.py
│   │   └── test_gold_facts.py
│   └── integration/                  ← End-to-end tests
│       └── test_pipeline_e2e.py
│
├── scripts/
│   ├── validate_adf_json.py
│   └── deploy_jobs.py
│
├── docs/
│   ├── architecture_overview.md
│   └── naming_conventions.md
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Project Roadmap

| Phase | Description                     | Status         |
|-------|---------------------------------|----------------|
| 0     | Azure Infrastructure Setup      | 🚧 In Progress |
| 1     | Data Generation (SQL Server)    | ⏳ Pending     |
| 2     | CSV/JSON + Event Hubs Producers | ⏳ Pending     |
| 3     | ADF Pipelines + SHIR            | ⏳ Pending     |
| 4     | Databricks Medallion            | ⏳ Pending     |
| 5     | Streaming Layer (Event Hubs)    | ⏳ Pending     |
| 6     | Monitoring & Governance         | ⏳ Pending     |
| 7     | CI/CD GitHub Actions            | ⏳ Pending     |
| 8     | Power BI Dashboards             | ⏳ Pending     |
| 9     | Documentation & LinkedIn        | ⏳ Pending     |

---

## License

This project is licensed under the [MIT License](LICENSE).
Free to use, modify, and share with proper attribution.
