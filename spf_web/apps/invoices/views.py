import os.path
import time
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from helpers.auth import user_allowed_society
from spf_web.apps.invoices.models import Invoice
from spf_web.apps.society.models import Society, Event
from .f60 import f60


@login_required
def redirect_society(request):
    return redirect(index, society_name=request.user.spfuser.society.shortname)


@login_required
def index(request, society_name):
    society = get_object_or_404(Society, shortname=society_name)
    if not user_allowed_society(request.user, society):
        return render(request, "errors/unauthorized.jinja")

    events = Event.objects.filter(society=society)
    proc_vals = events.values('processed').distinct().exclude(processed__isnull=True).order_by('-processed')
    invoices = Invoice.objects.filter(society=society).order_by('-period')

    return render(request, "invoices/index.jinja",
                  {'proc_vals': proc_vals, 'cur_page': 'invoices', 'invoices': invoices})


def unix_time(dt):
    return int(time.mktime(dt.timetuple()))


def generate(request, society_name, date):
    society = get_object_or_404(Society, shortname=society_name)

    events = Event.objects.filter(society=society, processed=date)
    invoice_obj = Invoice.objects.get(society=society, period=date)

    filename = os.path.join("static_invoice", society.shortname + "-" + str(date) + ".pdf")
    if os.path.isfile(filename):
        return HttpResponse(open(filename, "rb"), content_type="application/pdf")

    invoice = f60(filename, overskriv=True)
    invoice.settKundeinfo(1, society.name)
    invoice.settFakturainfo(
        fakturanr=1,
        utstedtEpoch=unix_time(events[0].processed),
        forfallEpoch=unix_time(events[0].processed) + 3600 * 24 * 7,
        fakturatekst="Faktura fra SPF for utlan.\nFaktura nr " + str(invoice_obj.invoice_number))
    invoice.settFirmainfo(
        {
            'firmanavn': "Studentkjellernes Personalforening",
            'kontaktperson': '',
            'kontonummer': 60940568407,
            'organisasjonsnummer': 890747272,
            'addresse': 'Problemveien 13,\nv/ Bunnpris Blindern, Postboks 71',
            'postnummer': '0313',
            'poststed': 'Oslo',
            'telefon': '',
            'epost': 'spf-styret@studorg.uio.no'
        })

    linjer = []
    totcost = 0
    for e in events:
        linjer.append(["" + str(e.date) + ": " + e.name, 1, e.get_cost(), 0])
        totcost += e.get_cost()

    totcost = totcost.quantize(Decimal(10) ** -2)
    spf_fee = totcost * Decimal("0.30")
    linjer.append(["SPF-avgift: " + str(totcost) + "*0.3", 1, spf_fee, 0])

    invoice.settOrdrelinje(linjer)
    invoice.lagEpost()

    return HttpResponse(open(filename, "rb"), content_type="application/pdf")


@login_required
def invoices_list(request):
    invoices = Invoice.objects.all().order_by('-invoice_number')
    return render(request, "invoices/list.jinja", {'invoices': invoices})


@login_required
@transaction.atomic
def invoices_all(request):
    if request.method == "POST":
        if request.POST.get('action') == "close_period":
            if not request.user.has_perm("invoice.close_period"):
                raise PermissionDenied()

            events = Event.objects.filter(processed__isnull=True)
            societies = events.values('society').distinct()
            period = timezone.now()
            for soc in societies:
                soc = Society.objects.get(id=soc['society'])
                print("Society=" + str(soc))
                invoice_number = Invoice.objects.all().aggregate(Max('invoice_number')).get('invoice_number__max')
                print("InvNo=" + str(invoice_number))
                if invoice_number is None:
                    invoice_number = 1
                else:
                    invoice_number += 1

                inv = Invoice(
                    society=soc,
                    invoice_number=invoice_number,
                    period=period
                )
                inv.save()
                for event in events.filter(society=soc):
                    print("->Event: " + str(event))
                    event.invoice = inv
                    event.processed = period
                    event.save()
            return redirect(invoices_all)
        elif request.POST.get('action') == 'mark_paid':
            if not request.user.has_perm('invoice.mark_paid'):
                raise PermissionDenied()
            invoice = Invoice.objects.get(id=request.POST.get('inv_id'))
            invoice.paid = True
            invoice.save()
            print("Marking as paid: " + str(invoice))
            return redirect(invoices_all)

    return render(request, "invoices/all.jinja",
                  {
                      'unprocessed_events': Event.objects.filter(processed__isnull=True).count(),
                      'invoices': Invoice.objects.filter(paid=False),
                  });