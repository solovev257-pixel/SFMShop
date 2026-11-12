# Развёртывание SFMShop в Kubernetes

Манифесты лежат в папке `k8s/`:

- `deployment.yaml` — Deployment на 3 реплики приложения. Если Pod упадёт, Kubernetes сам поднимет новый.
- `service.yaml` — Service типа LoadBalancer. Находит Pod'ы по метке `app: sfmshop` и отдаёт трафик с порта 80 на порт приложения 8000.

## Подготовка

Образ собирается из того же Dockerfile, что и для docker compose:

    docker build -f docker/Dockerfile -t sfmshop:latest .

## Secret с паролем базы

Пароль не пишем в манифест, потому что манифест лежит в git. Создаём Secret один раз прямо в кластере:

    kubectl create secret generic sfmshop-secrets --from-literal=DB_PASSWORD=<пароль>

В `deployment.yaml` переменная `DB_PASSWORD` берётся из этого Secret через `secretKeyRef`. Остальные переменные (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `REDIS_HOST`) названы так же, как их читает код. Проверить, что Secret есть: `kubectl get secrets`.

## Деплой

    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml

Проверка:

    kubectl get pods          # три Pod'а в статусе Running
    kubectl get services      # внешний адрес sfmshop-service
    kubectl logs -f deployment/sfmshop-deployment

В Deployment настроены проверки: `livenessProbe` на `/health/live` перезапускает зависший Pod, `readinessProbe` на `/health/ready` пускает трафик только на Pod, который уже подключился к базе.

## Масштабирование

Вручную поменять число копий:

    kubectl scale deployment sfmshop-deployment --replicas=5

Или поменять `replicas` в `deployment.yaml` и снова сделать `kubectl apply`.

Автоматически по нагрузке — через HorizontalPodAutoscaler: он добавляет Pod'ы, когда растёт загрузка CPU, и убирает, когда нагрузка падает.

    kubectl autoscale deployment sfmshop-deployment --min=2 --max=8 --cpu-percent=60
