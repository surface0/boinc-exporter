FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY boinc_exporter/ ./boinc_exporter/

EXPOSE 9101

CMD ["python", "-m", "boinc_exporter"]
