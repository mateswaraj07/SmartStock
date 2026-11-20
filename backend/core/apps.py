from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _seed(sender, **kwargs):
    from .seed import seed_master
    seed_master()


class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        post_migrate.connect(_seed, sender=self)
