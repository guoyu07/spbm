from django.contrib import admin

from . import events, worker
from ..models import Society, Invoice

"""
These things are so small that there's no point in giving them their own files.
I mean, really, it's just more mess than it's worth. // Thor
"""


class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('period', 'paid')
    inlines = [events.EventInline]


admin.site.register(Invoice, InvoiceAdmin)


class SocietyAdmin(admin.ModelAdmin):
    list_display = ('name', 'shortname', 'invoice_email',)


admin.site.register(Society, SocietyAdmin)
