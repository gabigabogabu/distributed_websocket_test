FROM python:3.9

COPY server.py server.py
COPY req req
RUN pip install -r req

CMD uvicorn server:app --host 0.0.0.0