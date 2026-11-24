FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements-runtime.txt backend/constraints.txt ./
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    pip install --no-cache-dir -c constraints.txt -r requirements-runtime.txt && mkdir /data && chown 10001:10001 /data
COPY --chown=10001:10001 backend/app ./app
COPY --chown=10001:10001 backend/scripts ./scripts
COPY --chown=10001:10001 ml/src/demand_lookup.py ml/src/safarnama_predictor.py ./ml/src/
COPY --chown=10001:10001 ml/outputs/demo_route_predictions.csv ml/outputs/safarnama_prediction_manifest.json ml/outputs/safarnama_prediction_schema.json ./ml/outputs/
ENV SAFARNAMA_ML_ARTIFACT_DIR=/app/ml/outputs
USER 10001:10001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
