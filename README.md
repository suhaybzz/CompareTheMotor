# CompareTheMotor

CompareTheMotor is a full-stack decision support web application designed to help users compare vehicles clearly, quickly, and confidently. The system addresses the problem of information overload in car purchasing by presenting structured, interpretable comparisons based on key metrics.

---

## Project Overview

This project was developed as part of a final year dissertation in Computer Science. It implements a rule-based comparison engine that evaluates vehicles across three core dimensions:

- Affordability  
- Efficiency  
- Performance  

Users can select vehicles manually or use a registration lookup feature to retrieve and enrich vehicle data before comparison.

---

## Key Features

- Side-by-side vehicle comparison  
- Rule-based scoring system with proportional evaluation  
- Buyer-priority weighting (Balanced, Affordability, Efficiency, Performance)  
- Registration-based lookup flow (DVLA API integration / demo mode)  
- Structured recommendation output  
- Clean and responsive user interface  

---

## System Architecture

The application follows a simple full-stack architecture:

- Frontend: HTML, CSS, JavaScript  
- Backend: Python (Flask)  
- Database: SQLite  

The frontend communicates with the backend via REST API calls. The backend processes requests, retrieves data from the database, applies the scoring model, and returns structured JSON responses.

---

## Scoring Model

The system uses a proportional rule-based scoring approach:

- Lower-is-better metrics (price, insurance group, CO₂) are inverted proportionally  
- Higher-is-better metrics (MPG, horsepower) are scaled proportionally  
- Scores are weighted according to user-selected priorities  
- Final outputs are interpretable and directly linked to input criteria  

This ensures that results are transparent, explainable, and responsive to user preferences.

---

## How to Run the Project

1. Navigate to the backend directory:
cd backend

2. Create a virtual environment:
python3 -m venv .venv  
source .venv/bin/activate  

3. Install dependencies:
pip install -r requirements.txt  

4. Run the Flask application:
python app.py  

5. Open the application in your browser:
http://127.0.0.1:5000  

---

## Data and API Integration

The system uses a local SQLite database containing vehicle records.  

A registration lookup feature is implemented using:
- A demo lookup dataset (included)
- Optional integration with the DVLA Vehicle Enquiry Service API  

API keys are managed via environment variables and are not included in this repository for security reasons.

---

## Project Status

This repository contains the final implementation submitted for the dissertation and represents a complete working system.

---

## Author
Suhayb Ahmed
Final Year Project – BSc Computer Science  (Goldsmiths, University of London)
CompareTheMotor Dissertation Project
