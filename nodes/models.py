from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .profile import clean_email, hash_email
# Create your models here.


class SocialNodes(models.Model):
    pass


class Node(models.Model):
    user = models.OneToOneField(
        User,
        related_name="node",
        on_delete=models.CASCADE
    )
    dp = models.ImageField(
        blank=True,
        null=True
    )

    def get_dp_url(self):
        if self.dp:
            return self.dp.url
        if self.user.email:
            token = self.user.email
        else:
            token = self.user.username
        return "https://www.gravatar.com/avatar/{}".format(
            hash_email(clean_email(token))
        )

    def __str__(self):
        return self.user.username


class Notification(models.Model):
    class Levels(models.TextChoices):
        ERROR = ("ERROR", "error")
        SUCCESS = ("SUCCESS", "success"),
        WARNING = ("WARNING", "warning"),
        INFO = ("INFO", "info")

    class Statuses(models.TextChoices):
        SENT = ("S", "sent")
        DELIVERED = ("D", "delivered")
        READ = ("R", "read")

    message = models.TextField()
    node = models.ForeignKey(
        Node,
        related_name="notifications",
        on_delete=models.CASCADE
    )
    level = models.CharField(
        max_length=22,
        choices=Levels.choices,
        default=Levels.INFO
    )
    created = models.DateTimeField(
        default=timezone.now
    )
    status = models.CharField(
        max_length=10,
        choices=Statuses.choices,
        default=Statuses.SENT
    )