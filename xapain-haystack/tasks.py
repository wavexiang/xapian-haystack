from time import sleep
from django.db import models
from celery import shared_task
from django.apps import apps
from django.conf import settings
from haystack import connections  as haystack_connections, connection_router
from haystack.exceptions import NotHandled
from redis import Redis

UPDATE_LOCK_KEY = 'xapian_lock'

redis = Redis.from_url(settings.REDIS_URL)


@shared_task()
def update_index(app_label, pk, is_save):
    """
    更新缓存

    算法：
        通过维护redis中的锁，确保事务的串行

    :param app_label: 模型名
    :param pk: id
    :param is_save: 是否是保存. true:保存(insert/update) false:删除delete
    :return:
    """

    app_name, model_name = app_label.split('.')
    app = apps.get_app_config(app_name)
    model = app.get_model(model_name)

    instance = model.objects.filter(pk=pk).first()
    if instance is None:
        return

    using_backends = connection_router.for_write(instance=instance)

    for using in using_backends:
        try:
            index = haystack_connections[using].get_unified_index().get_index(instance._meta.model)
            do_update_index(instance, index, using, is_save)
        except NotHandled:
            # TODO: Maybe log it or let the exception bubble?
            continue


def do_update_index(instance, index, using, is_save):
    """
    更新索引
    :param using:
    :param instance:
    :param index:
    :param is_save:
    :return:
    """
    # 获取锁
    while True:
        # 只有键不存在(nx，才设置)；过期时间10s，设置的值未locked
        locked = redis.set(UPDATE_LOCK_KEY, 'locked', ex=10, nx=True)
        if not locked:
            sleep(0.5)
            continue
        else:
            break

    if is_save:
        index.update_object(instance, using=using)
    else:
        index.remove_object(instance, using=using)
    redis.delete(UPDATE_LOCK_KEY)
