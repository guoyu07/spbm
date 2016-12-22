from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import six
from django.utils.functional import lazy
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

mark_safe_lazy = lazy(mark_safe, six.text_type)


class Society(models.Model):
    name = models.CharField(max_length=100)
    shortname = models.CharField(max_length=10)
    invoice_email = models.EmailField(default="")
    default_wage = models.DecimalField(max_digits=10, decimal_places=2)
    logo = models.FileField(null=True)

    def __str__(self):
        return self.shortname


class Worker(models.Model):
    """
    Model for student -- and other types of -- workers.
    """
    society = models.ForeignKey(Society, on_delete=models.PROTECT, related_name="workers")
    active = models.BooleanField(default=True,
                                 verbose_name=_('active'),
                                 help_text=_('Check off if the worker is still actively working.'))
    name = models.CharField(max_length=1000,
                            verbose_name=_('name'),
                            help_text=_('Full name, with first name first.'))
    address = models.CharField(max_length=1000,
                               verbose_name=_('address'),
                               help_text=_('Full address including postal code and area.'))
    account_no = models.CharField(max_length=20,
                                  blank=True,
                                  verbose_name=_('account no.'),
                                  help_text=_('Norwegian bank account number, no periods, 11 digits.'))
    person_id = models.CharField(max_length=20,
                                 blank=True)
    norlonn_number = models.IntegerField(blank=True,
                                         null=True,
                                         unique=True,
                                         verbose_name=_("norl&oslash;nn number"),
                                         help_text=mark_safe_lazy(_(
                                             "Employee number in the wage system, Norl&oslash;nn. " +
                                             "<strong>Must</strong> exist and be correct!")))

    def __str__(self):
        return self.name + " (" + self.society.shortname + ")"


class Event(models.Model):
    society = models.ForeignKey(Society, null=False, related_name="society", on_delete=models.PROTECT)
    name = models.CharField(max_length=100,
                            verbose_name=_('name'))
    date = models.DateField(verbose_name=_('event date'))
    registered = models.DateField(auto_now_add=True,
                                  editable=False,
                                  verbose_name=_('registered'))
    processed = models.DateField(null=True,
                                 blank=True,
                                 verbose_name=_('processed'))
    invoice = models.ForeignKey('invoices.Invoice',
                                null=True,
                                blank=True,
                                related_name="in_invoice",
                                verbose_name=_('invoice'))

    def __str__(self):
        return self.society.shortname + " - " + str(self.date) + ": " + self.name

    def get_cost(self):
        total = Decimal(0)
        for s in self.shift_set.all():
            total += s.get_total()
        total = total.quantize(Decimal(".01"))
        return total

    get_cost.short_description = _("Total cost")

    def clean(self):
        if self.invoice is not None:
            if self.invoice.society != self.society:
                raise ValidationError("Cannot add event to another society invoice!")


class Shift(models.Model):
    event = models.ForeignKey(Event, related_name="event")
    worker = models.ForeignKey(Worker,
                               on_delete=models.PROTECT,
                               related_name="worker",
                               verbose_name=_('worker'))
    wage = models.DecimalField(max_digits=10,
                               decimal_places=2,
                               verbose_name=_('wage'))
    hours = models.DecimalField(max_digits=10,
                                decimal_places=2,
                                verbose_name=_('hours'))
    norlonn_report = models.ForeignKey('norlonn.NorlonnReport',
                                       blank=True,
                                       null=True,
                                       on_delete=models.SET_NULL,
                                       related_name="in_report",
                                       verbose_name=_('norl&oslash;nn report'))

    norlonn_report.short_description = "Sent to norlønn"

    class Meta:
        unique_together = ("event", "worker")

    def clean(self):
        try:
            if self.worker.society != self.event.society:
                raise ValidationError("Worker on shift does not belong to the same society as the event")
        except:
            raise ValidationError("No worker or event")

    def get_total(self):
        return (self.wage * self.hours).quantize(Decimal(".01"))