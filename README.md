<div align="center">

# 🚢 Maritime Lakehouse Platform

### End-to-end Azure Data Engineering · Medallion Architecture

[![Azure](https://img.shields.io/badge/Azure-Databricks-FF3621?style=flat-square&logo=apachedatabricks&logoColor=white)](https://azure.microsoft.com)
[![Delta Lake](https://img.shields.io/badge/Delta-Lake-00ADD8?style=flat-square&logo=delta&logoColor=white)](https://delta.io)
[![Unity Catalog](https://img.shields.io/badge/Unity-Catalog-1B3A6B?style=flat-square&logo=databricks&logoColor=white)](https://databricks.com)
[![Power BI](https://img.shields.io/badge/Power-BI-F2C811?style=flat-square&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com)
[![Great Expectations](https://img.shields.io/badge/Great-Expectations-FF6B6B?style=flat-square)](https://greatexpectations.io)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

<br/>

> A production-grade maritime logistics data platform built on Azure —
> ingesting, transforming, and governing 870K+ rows across 8 business domains
> with 100/100 data quality checks and full lineage tracking.

<br/>

![Architecture](docs/architecture.png)

</div>

---

## 📐 Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  SOURCES          INGESTION         STORAGE            PROCESSING            │
│                                                                               │
│  SQL Server  ──→  ADF + SHIR   ──→  landing/erp/  ──→  Bronze Layer         │
│  CSV Files   ──→  Python       ──→  landing/files/ ──→  Silver Layer  ──→  Gold │
│  JSON Files  ──→  Upload       ──→                                           │
│  Event Hubs  ──→  Streaming    ──→  landing/stream/     (Phase 5)            │
│                                                                               │
│  ─────────────────────────────────────────────────────────────────────────── │
│  GOVERNANCE : Unity Catalog · Microsoft Purview · Azure Key Vault            │
│  QUALITY    : Delta Constraints · Great Expectations · 100/100 checks        │
│  SERVING    : Power BI DirectQuery · 6 Dashboards                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Tech Stack

<table>
<tr>
<td><b>Layer</b></td>
<td><b>Technology</b></td>
<td><b>Purpose</b></td>
</tr>
<tr>
<td>Sources</td>
<td>SQL Server 2019 · CSV · JSON · Event Hubs</td>
<td>3 source types · 8 business domains</td>
</tr>
<tr>
<td>Ingestion</td>
<td>Azure Data Factory + SHIR · Python</td>
<td>Batch + file ingestion</td>
</tr>
<tr>
<td>Storage</td>
<td>ADLS Gen2 — adlsmaritimedev</td>
<td>Landing · Bronze · Silver · Gold</td>
</tr>
<tr>
<td>Processing</td>
<td>Azure Databricks · Spark 3.5</td>
<td>Medallion transformation pipeline</td>
</tr>
<tr>
<td>Table Format</td>
<td>Delta Lake</td>
<td>ACID · Time Travel · Schema Evolution</td>
</tr>
<tr>
<td>Governance</td>
<td>Unity Catalog · Microsoft Purview</td>
<td>Lineage · RBAC · Glossary · Scanning</td>
</tr>
<tr>
<td>Data Quality</td>
<td>Delta Constraints · Great Expectations</td>
<td>100/100 checks — Silver layer</td>
</tr>
<tr>
<td>Secrets</td>
<td>Azure Key Vault Secret Scope</td>
<td>Zero credentials in code</td>
</tr>
<tr>
<td>Orchestration</td>
<td>Databricks Workflow</td>
<td>5 tasks DAG · Daily 06:00 UTC</td>
</tr>
<tr>
<td>Serving</td>
<td>Power BI Desktop</td>
<td>6 dashboards · DirectQuery</td>
</tr>
<tr>
<td>CI/CD</td>
<td>GitHub Actions</td>
<td>Automated deployment</td>
</tr>
</table>

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
  → Examples: vessel_year >= 1900, quantity_mt > 0,
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

| Resource | Cost/month |
|---|---|
| Azure Databricks (DS3_v2) | ~$25 |
| ADLS Gen2 | ~$2 |
| Azure Data Factory | ~$3 |
| Event Hubs | ~$2 |
| **Total** | **~$32** |

> Budget alert configured at **$70/month** · Current spend: **$36.68 USD**

---

## 🗂️ Project Structure

```
maritime-lakehouse-platform/
├── 📓 databricks/
│   ├── config.ipynb                 # Global vars + ADLS auth
│   ├── bronze/
│   │   ├── bronze_erp.ipynb         # 16 ERP tables from SQL Server
│   │   ├── bronze_files.ipynb       # CSV fuelops + JSON weather
│   │   └── bronze_streaming.ipynb  # Event Hubs AIS + engine (Phase 5)
│   ├── silver/
│   │   ├── silver_erp.ipynb         # Clean + type + DQ · 16 tables
│   │   └── silver_files.ipynb       # Normalize + enrich · 3 tables
│   └── gold/
│       └── gold.ipynb               # Star schema · 9 data products
├── 🐍 data_generators/
│   ├── generate_maritime_data.py    # SQL Server synthetic data
│   ├── generate_fuelops_csv.py      # CSV fuelops generator
│   ├── generate_weather_json.py     # JSON weather generator
│   ├── producer_ais.py              # AIS Event Hubs producer
│   └── producer_engine_metrics.py  # Engine metrics producer
├── 🔧 adf/
│   ├── pipeline/                    # pl_sqlserver_to_adls_maritime
│   ├── dataset/                     # ds_sqlserver + ds_adls_parquet
│   └── linkedService/              # ls_sqlserver + ls_adls
├── 📐 docs/
│   └── architecture.png
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

# 2. Upload files to ADLS
python data_generators/upload_to_adls.py

# 3. Run ADF pipeline
# → adf-maritime-dev → pl_sqlserver_to_adls_maritime → Trigger now

# 4. Run Databricks Workflow
# → dbw-maritime-dev → Workflows → maritime_lakehouse_pipeline → Run now
```

---

---

## 👤 Author

<div align="center">

**Youssouf Abdouramane**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/youssouf-abdouramane)
[![GitHub](https://img.shields.io/badge/GitHub-YoussoufDS-181717?style=flat-square&logo=github)](https://github.com/YoussoufDS)

</div>
