#!/bin/bash
# run_project.sh
# Script to install requirements, ingest data, and start server

echo "=========================================="
echo " Starting School Dropout Analysis System "
echo "=========================================="

echo "[1/3] Installing Python packages..."
# Using --user to avoid virtualenv permissions completely if that was the prior issue
pip install -r requirements.txt 

echo "[2/3] Generating Mock Data and Updating MongoDB..."
# Uses PyMongo to insert records
python3 generate_data_and_load.py

echo "[3/3] Launching Django Application Analytics Engine..."
python3 manage.py runserver

echo "=========================================="
echo " Dashboard running at: http://127.0.0.1:8000 "
echo "=========================================="
