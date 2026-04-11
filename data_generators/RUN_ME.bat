@echo off
echo ============================================
echo  Maritime Lakehouse - Setup et Generation
echo ============================================

echo.
echo [1/2] Installation des packages...
pip install pyodbc sqlalchemy pandas faker numpy python-dateutil tqdm azure-eventhub azure-storage-blob

echo.
echo [2/2] Lancement du generateur...
python generate_maritime_data.py

echo.
echo Termine! Verifiez MaritimeDB dans SSMS.
pause
