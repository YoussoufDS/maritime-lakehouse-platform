@echo off
echo ============================================
echo  Maritime Lakehouse - Generate FUELOPS CSV
echo ============================================
echo.
pip install faker
python generate_fuelops_csv.py
echo.
echo Done! Upload output_files/landing/files/fuelops/ to ADLS
pause
