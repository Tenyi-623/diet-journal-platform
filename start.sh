cd /home/aitd/hypertension-diet

# Docker 已运行时，再执行 start 也可以。
sudo systemctl start docker

# 启动本项目的数据库，复用原数据卷。
sudo docker compose up -d db

# 等待 db 状态变成 healthy。
sudo docker compose ps

# 正常时应包含 accepting connections。
sudo docker compose exec -T db pg_isready -U diet_app -d hypertension_diet
```