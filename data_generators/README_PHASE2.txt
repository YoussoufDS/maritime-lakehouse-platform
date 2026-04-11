===============================================
 Maritime Lakehouse Platform - Phase 2
 Source 2 : CSV/JSON Files
 Source 3 : Event Hubs Streaming
===============================================

ETAPE 1 - Generer les fichiers CSV/JSON
----------------------------------------
Ouvrir Anaconda Prompt :
  conda activate maritime-lakehouse
  cd data_generators

Generer FUELOPS :
  python generate_fuelops_csv.py
  --> Cree output_files/landing/files/fuelops/

Generer WEATHER :
  python generate_weather_json.py
  --> Cree output_files/landing/files/weather/

ETAPE 2 - Uploader dans ADLS Gen2
-----------------------------------
1. Ouvrir portal.azure.com
2. Aller dans adlsmaritimedev
3. Container "landing"
4. Uploader les dossiers :
   output_files/landing/files/fuelops/ --> landing/files/fuelops/
   output_files/landing/files/weather/ --> landing/files/weather/

ETAPE 3 - Configurer les Producers Event Hubs
----------------------------------------------
1. Ouvrir producer_ais.py
2. Remplacer YOUR_EVENTHUB_CONNECTION_STRING
   par ta connection string Event Hubs
   (Azure Portal > evhns-maritime-dev > 
    Shared access policies > RootManageSharedAccessKey)
3. Faire pareil pour producer_engine_metrics.py

ETAPE 4 - Lancer les Producers
--------------------------------
Terminal 1 :
  python producer_ais.py

Terminal 2 :
  python producer_engine_metrics.py

Note : Les producers envoient en continu.
       Ctrl+C pour arreter.
       Garder actifs pendant Phase 4 (Databricks Streaming)
===============================================
