import redis
import json
from django.conf import settings

# Configuración de Redis (ajusta si usas otro host/puerto)
REDIS_HOST = getattr(settings, "REDIS_HOST", "localhost")
REDIS_PORT = getattr(settings, "REDIS_PORT", 6379)
REDIS_DB = getattr(settings, "REDIS_DB", 0)

redis_client = redis.StrictRedis(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
)


def set_task_progress(task_id, data):
    print(f"[PROGRESS][SET] task_id={task_id} data={data}")
    redis_client.set(
        f"task_progress:{task_id}", json.dumps(data), ex=60 * 60 * 6
    )  # 6 horas de expiración


def get_task_progress(task_id):
    val = redis_client.get(f"task_progress:{task_id}")
    print(f"[PROGRESS][GET] task_id={task_id} found={val is not None}")
    if val:
        return json.loads(val)
    return None
