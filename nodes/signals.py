from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import (
    User, Node
)
