from django.db import models
from django.contrib.localflavor.us.models import USStateField

from ostracker.models import Project, Contributor


class StateStatus(models.Model):
    state = USStateField()
    bills = models.BooleanField(default=False)
    bill_versions = models.BooleanField(default=False)
    sponsors = models.BooleanField(default=False)
    legislators = models.BooleanField(default=False)
    committees = models.BooleanField(default=False)
    actions = models.BooleanField(default=False)
    votes = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    owner = models.CharField(max_length=50, blank=True)
    num_commits = models.IntegerField(default=0)
    latest_commit = models.DateTimeField(null=True)

    repositories = models.ManyToManyField(Project, related_name='states')

    contributors = models.ManyToManyField(Contributor, related_name='states')

    def completeness(self):
        return sum((self.bills, self.bill_versions, self.sponsors,
                    self.legislators, self.committees, self.actions,
                    self.votes)) / 7.0

    def __unicode__(self):
        return self.state
