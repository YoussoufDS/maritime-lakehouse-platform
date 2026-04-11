<div align="center">

# 🚢 Maritime Lakehouse Platform

### End-to-end Azure Data Engineering · Medallion Architecture

[![Azure](https://img.shields.io/badge/Azure-Databricks-FF3621?style=flat-square&logo=apachedatabricks&logoColor=white)](https://azure.microsoft.com)
[![Delta Lake](https://img.shields.io/badge/Delta-Lake-00ADD8?style=flat-square&logoColor=white)](https://delta.io)
[![Unity Catalog](https://img.shields.io/badge/Unity-Catalog-1B3A6B?style=flat-square&logo=databricks&logoColor=white)](https://databricks.com)
[![Power BI](https://img.shields.io/badge/Power-BI-F2C811?style=flat-square&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com)
[![Great Expectations](https://img.shields.io/badge/Great-Expectations-FF6B6B?style=flat-square)](https://greatexpectations.io)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

<br/>

> A production-grade maritime logistics data platform built on Azure —
> ingesting, transforming, and governing **870K+ rows** across **8 business domains**
> with **100/100 data quality checks** and full lineage tracking.

</div>

---

## 📐 Architecture

![Architecture](docs/Maritime_diagram_project_drawio.png)

---

## ⚡ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Sources | SQL Server 2019 · CSV · JSON · Event Hubs | 3 source types · 8 business domains |
| Ingestion | Azure Data Factory + SHIR · Python | Batch + file ingestion |
| Storage | ADLS Gen2 — adlsmaritimedev | Landing · Bronze · Silver · Gold |
| Processing | Azure Databricks · Spark 3.5 | Medallion transformation pipeline |
| Table Format | Delta Lake | ACID · Time Travel · Schema Evolution |
| Governance | Unity Catalog · Microsoft Purview | Lineage · RBAC · Glossary · Scanning |
| Data Quality | Delta Constraints · Great Expectations | 100/100 checks — Silver layer |
| Secrets | Azure Key Vault Secret Scope | Zero credentials in code |
| Orchestration | Databricks Workflow | 5 tasks DAG · Daily 06:00 UTC |
| Serving | Power BI Desktop | 6 dashboards · DirectQuery |
| CI/CD | GitHub Actions | Automated deployment |

---

## 📦 Data Volume

| Layer | Tables | Rows | Description |
|---|---|---|---|
| 🟤 Bronze ERP | 16 | 116,222 | Raw SQL Server → Parquet via ADF |
| 🟤 Bronze Files | 3 | 169,070 | CSV fuelops + JSON weather |
| 🔵 Silver ERP | 16 | 141,222 | Typed · Deduplicated · Validated |
| 🔵 Silver Files | 3 | 203,482 | Normalized · Enriched · DQ checked |
| 🟡 Gold | 9 | 242,788 | Star schema · Data products |
| **Total** | **47** | **872,784** | |

---

## 🗄️ Source Data — SQL Server 2019

16 tables · 116,222 rows ingested via ADF + Self-Hosted Integration Runtime

![SQL Server](docs/Capture%20d'%C3%A9cran%202026-04-06%20155117.png)

---

## 📡 Streaming — Azure Event Hubs

2 active streams · 29,430 messages · 13.59 MB ingested over 7 days

![Event Hubs](docs/Capture%20d'%C3%A9cran%202026-04-06%20160115.png)

### AIS Positions Stream — 630 events

![AIS Stream](docs/Capture%20d'%C3%A9cran%202026-04-06%20160432.png)

### Engine Metrics Stream — 120 events

![Engine Stream](docs/Capture%20d'%C3%A9cran%202026-04-06%20160540.png)

---

## 🗂️ Landing Zone — ADLS Gen2

### Container structure — 3 folders

![ADLS Landing](docs/Capture%20d'%C3%A9cran%202026-04-11%20171231.png)

### ERP domain organization — 7 business domains

![ADLS ERP](docs/Capture%20d'%C3%A9cran%202026-04-11%20171528.png)

---

## 🏛️ Business Domains

```
maritime_dev (Unity Catalog)
├── 🟤 bronze_fleet          ├── 🔵 silver_fleet
├── 🟤 bronze_navigation     ├── 🔵 silver_navigation
├── 🟤 bronze_portops        ├── 🔵 silver_portops
├── 🟤 bronze_cargo          ├── 🔵 silver_cargo
├── 🟤 bronze_fuelops        ├── 🔵 silver_fuelops
├── 🟤 bronze_crewing        ├── 🔵 silver_crewing
├── 🟤 bronze_commercial     ├── 🔵 silver_commercial
└── 🟡 gold
    ├── dim_vessel · dim_port · dim_date
    └── fact_voyage · fact_port_call · fact_cargo
        fact_bunkering · fact_consumption · fact_crew
```

---

## ✅ Data Quality

Two-layer enforcement strategy across all 19 Silver tables:

```
Layer 1 — Delta CHECK Constraints (hard enforcement)
  → Blocks invalid writes at table level
  → Examples: build_year >= 1900, quantity_mt > 0,
              latitude BETWEEN -90 AND 90

Layer 2 — Great Expectations (statistical validation)
  → Validates distributions, uniqueness, nulls, ranges
  → 100/100 checks passing ✅
```

| Notebook | Checks | Status |
|---|---|---|
| silver_erp | 80/80 | ✅ |
| silver_files | 20/20 | ✅ |
| **Total** | **100/100** | **✅** |

---

## 🟡 Gold Layer — Data Products

Each table is a governed data product with schema contract, quality SLA, owner, lineage, and consumption interface.

| Data Product | Type | Rows | Key Metrics |
|---|---|---|---|
| `dim_vessel` | Dimension | 150 | Class · flag · tonnage enriched |
| `dim_port` | Dimension | 20 | Terminal count · max depth |
| `dim_date` | Dimension | 2,557 | 2020–2026 · week · quarter |
| `fact_voyage` | Fact | 18,000 | Duration · speed · status |
| `fact_port_call` | Fact | 26,921 | Port stay hours · purpose |
| `fact_cargo` | Fact | 25,000 | Revenue · tonnage · freight rate |
| `fact_bunkering` | Fact | 12,000 | Cost · grade · supplier |
| `fact_consumption` | Fact | 150,140 | EEOI · CII rating · efficiency |
| `fact_crew` | Fact | 8,000 | Assignment days · rank |

---

## 🔒 Governance

### Unity Catalog
```
17 schemas · Column-level lineage · RBAC · Audit logs
Zero-copy data sharing across workspaces
```

### Microsoft Purview
```
Automated scanning — ADLS Gen2 + Databricks Unity Catalog
Business Glossary — Vessel · Voyage · Bunkering Event · CII Rating · Port Call
End-to-end lineage — SQL Server → ADF → ADLS → Databricks → Power BI
Data classification — PII detection on seafarers + clients
```

### Azure Key Vault
```python
# Zero credentials in code
adls_access_key = dbutils.secrets.get(
    scope="maritime-kv",
    key="adls-access-key"
)
```

---

## 🔄 Pipeline Orchestration

```
Databricks Workflow — maritime_lakehouse_pipeline

bronze_erp ──────────────→ silver_erp ──→
                                           gold  →  Power BI
bronze_files ────────────→ silver_files →

Schedule : Daily 06:00 UTC (America/Toronto)
Duration : ~16 min end-to-end
```

| Task | Duration | Depends on |
|---|---|---|
| bronze_erp | ~118s | — |
| bronze_files | ~189s | — |
| silver_erp | ~260s | bronze_erp |
| silver_files | ~189s | bronze_files |
| gold | ~219s | silver_erp, silver_files |

---

## 📊 Power BI Dashboards

| Dashboard | Key Visuals |
|---|---|
| Fleet Overview | Fleet by type · flag · vessel age distribution |
| Voyage Analytics | Monthly voyages · completion rate · avg duration |
| Port Operations | Busiest ports · port stay hours · activity map |
| Cargo & Revenue | Revenue by type · monthly trend · freight rate |
| Fuel & CII Rating | EEOI by vessel · CII A-E distribution · consumption |
| Crew Dashboard | Crew by rank · nationalities · assignments timeline |

---

## 💰 Cost Management

![Budget](docs/Capture%20d'%C3%A9cran%202026-04-11%20171603.png)

> Budget: **$70/month** · Current spend: **$36.68 USD** · 4 alert thresholds (50% · 75% · 90% · 100%)

---

## 🗂️ Project Structure

```
maritime-lakehouse-platform/
├── 📓 databricks/
│   ├── config.ipynb
│   ├── bronze/
│   │   ├── bronze_erp.py
│   │   ├── bronze_files.py
│   │   └── bronze_streaming.py
│   ├── silver/
│   │   ├── silver_erp.py
│   │   └── silver_files.py
│   └── gold/
│       └── gold.py
├── 🐍 data_generators/
│   ├── generate_maritime_data.py
│   ├── generate_fuelops_csv.py
│   ├── generate_weather_json.py
│   ├── producer_ais.py
│   └── producer_engine_metrics.py
├── 🔧 adf/
│   ├── pipeline/
│   ├── dataset/
│   └── linkedService/
├── 📐 docs/
│   ├── Maritime_diagram_project_drawio.png
│   └── screenshots/
├── README.md
├── requirements.txt
└── .gitignore
```

---

## 🚀 Setup

### Prerequisites
- Azure subscription (Azure for Students compatible)
- Azure Databricks Premium workspace
- SQL Server 2019 local + SHIR configured
- Python 3.11 + conda

### Installation

```bash
git clone https://github.com/YoussoufDS/maritime-lakehouse-platform
cd maritime-lakehouse-platform
conda create -n maritime-lakehouse python=3.11
conda activate maritime-lakehouse
pip install -r requirements.txt
```

### Run

```bash
# 1. Generate source data
python data_generators/generate_maritime_data.py
python data_generators/generate_fuelops_csv.py
python data_generators/generate_weather_json.py

# 2. Run ADF pipeline
# → adf-maritime-dev → pl_sqlserver_to_adls_maritime → Trigger now

# 3. Run Databricks Workflow
# → dbw-maritime-dev → Workflows → maritime_lakehouse_pipeline → Run now
```

---



---

<div align="center">

## 👤 Author

**Youssouf Abdouramane**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/youssouf-abdouramane)
[![GitHub](https://img.shields.io/badge/GitHub-YoussoufDS-181717?style=flat-square&logo=github)](https://github.com/YoussoufDS)

</div>
