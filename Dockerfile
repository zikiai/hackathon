FROM python:3.14-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
COPY integrated_app/requirements-cloud.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY integrated_app /app/integrated_app
COPY rail_corrugation/src /app/rail_corrugation/src
COPY door/src /app/door/src
COPY acv/src /app/acv/src
COPY shm/*.py /app/shm/
COPY shm/ui/serve.py /app/shm/ui/serve.py
COPY rail_corrugation/artifacts/rail_model.joblib /app/rail_corrugation/artifacts/rail_model.joblib
COPY door/artifacts/door_selected.joblib /app/door/artifacts/door_selected.joblib
COPY shm/shm_shape_model.joblib /app/shm/shm_shape_model.joblib
USER 10001:10001
WORKDIR /app/integrated_app
EXPOSE 8080
CMD ["sh","-c","exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 2 --timeout 900 --access-logfile - cloud_server:app"]
