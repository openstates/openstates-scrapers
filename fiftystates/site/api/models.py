import datetime

from django.db import models


class LogEntry(models.Model):
    caller_key = models.CharField(max_length=32)
    timestamp = models.DateTimeField(default=datetime.datetime.utcnow)
    method = models.CharField(max_length=128)

    query_string = models.TextField()

    class Meta:
        ordering = ('-timestamp',)

