from django.conf import settings
from haystack.exceptions import NotHandled
from haystack.signals import BaseSignalProcessor
from django.db import models

from extension.tasks import update_index


class QueuedSignalProcessor(BaseSignalProcessor):
    """
    排队的任务更新请求

    将更新请求排入celery队列，然后由celery中顺序更新，以解决并发问题。
    """

    def handle_save(self, sender, instance: models.Model, **kwargs):
        """
        Given an individual model instance, determine which backends the
        update should be sent to & update the object on those backends.
        """
        class_name = instance.__class__.__name__
        if class_name in ['Question', 'Paper', 'Knowledge', 'Course'] and instance.id is not None:
            app_label = '{}.{}'.format(instance._meta.app_label, instance._meta.model.__name__)
            update_index.apply_async([app_label, instance.id, True], countdown=settings.TASK_COUNTDOWN)

    def handle_delete(self, sender, instance, **kwargs):
        """
        Given an individual model instance, determine which backends the
        delete should be sent to & delete the object on those backends.
        """
        class_name = instance.__class__.__name__
        if class_name in ['Question', 'Paper', 'Knowledge', 'Course']:
            app_label = '{}.{}'.format(instance._meta.app_label, instance._meta.model.__name__)
            update_index.apply_async([app_label, instance.id, False], countdown=settings.TASK_COUNTDOWN)

    def setup(self):
        # Naive (listen to all model saves).
        models.signals.post_save.connect(self.handle_save)
        models.signals.post_delete.connect(self.handle_delete)
        # Efficient would be going through all backends & collecting all models
        # being used, then hooking up signals only for those.

    def teardown(self):
        # Naive (listen to all model saves).
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.post_delete.disconnect(self.handle_delete)
        # Efficient would be going through all backends & collecting all models
        # being used, then disconnecting signals only for those.
