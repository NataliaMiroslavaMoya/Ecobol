# 🌿 EcoBol – Asistente de biodiversidad y áreas protegidas de Bolivia

Frontend (HTML/CSS/JS) ⇄ Backend (Python/Flask) ⇄ Scraping (R).

```
frontend/ index.html · style.css · script.js
backend/  app.py · chatbot.py · data/base.csv · data/hechos.json · data/scraped.json
scraping/ scraping.R
```
## Ejecutar (CMD)
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
Rscript -e "install.packages(c('rvest','httr','jsonlite'), repos='https://cloud.r-project.org')"
Rscript scraping\scraping.R
python backend\app.py
```
Abre http://localhost:5000

## Agregar información
Añade filas a `backend/data/base.csv` y vuelve a correr `scraping.R`. Datos concretos (año de creación, superficie, estado UICN) van en `backend/data/hechos.json`.
Las categorías de la UICN son internacionales; no las confundas con las del Libro Rojo de Bolivia.
