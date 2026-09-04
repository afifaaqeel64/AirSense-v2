#!/bin/bash
# Load historical Lahore data — run once after first deployment
echo "Triggering historical data load via Airflow..."
curl -X POST "http://localhost:8080/api/v1/dags/airsense_historical_load/dagRuns" \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d '{"conf": {"city": "lahore"}}'
echo ""
echo "✓ Historical load triggered. Monitor at http://localhost:8080"
echo "  This will load 2018–present Lahore data from OpenAQ (~2-3 hours)"
