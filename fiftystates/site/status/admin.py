from django.contrib import admin

from fiftystates.site.status.models import StateStatus


class StatusAdmin(admin.ModelAdmin):
    list_display = ('state', 'bills', 'bill_versions', 'sponsors',
                    'legislators', 'actions', 'votes', 'owner',
                    'num_commits', 'latest_commit')
admin.site.register(StateStatus, StatusAdmin)
