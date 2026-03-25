FROM python:3.12-slim

RUN pip install --no-cache-dir aiohttp

COPY server.py .

EXPOSE 9999

CMD ["python", "server.py"]
