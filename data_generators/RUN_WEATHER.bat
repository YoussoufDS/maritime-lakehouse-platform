@echo off
echo ============================================
echo  Maritime Lakehouse - Generate WEATHER JSON
echo ============================================
echo.
pip install faker
python generate_weather_json.py
echo.
echo Done! Upload output_files/landing/files/weather/ to ADLS
pause
