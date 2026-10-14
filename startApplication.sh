cd /home/aitd/hypertension-diet
backend/.venv/bin/python -m scripts.service start
backend/.venv/bin/python -m scripts.service status

curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:8000/api/health