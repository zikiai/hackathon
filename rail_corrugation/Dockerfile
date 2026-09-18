FROM python:3.14-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLCONFIGDIR=/tmp/matplotlib
COPY requirements-runtime.txt pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements-runtime.txt && pip install --no-cache-dir --no-deps .
COPY app.py ./
COPY artifacts/rail_model.joblib artifacts/metrics.json artifacts/cross_validation_predictions.csv ./artifacts/
USER 10001:10001
EXPOSE 8080
CMD ["sh", "-c", "exec streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8080} --server.headless=true --browser.gatherUsageStats=false"]
