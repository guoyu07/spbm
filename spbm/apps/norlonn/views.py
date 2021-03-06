from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext as _

from spbm.helpers.auth import user_society
from .models import NorlonnReport
from ..society.models import Shift


@login_required
def index(request):
    reports = NorlonnReport.objects.all().order_by('-date')
    errors = []

    queryset = Shift.objects.select_related().prefetch_related('event__invoice').filter(norlonn_report__isnull=True,
                                                                                        event__processed__isnull=False)

    if request.user.has_perm('norlonn.generate_report'):
        shifts = queryset
    else:
        shifts = queryset.filter(event__society=user_society(request.user.spfuser))

    for s in shifts:
        if s.worker.norlonn_number is None:
            errors.append(_("Worker %s (for %s) lacks norlonn number!" % (s.worker, s.event)))

        if not s.event.invoice.paid:
            errors.append(_("%s (for %s) --- Invoice not paid" % (s.worker, s.event)))

    return render(request, 'norlonn/index.jinja', {'reports': reports, 'errors': errors})


@login_required
@permission_required('norlonn.generate_report')
def generate_report(request):
    if request.method != "POST":
        return redirect(index)

    errors = []
    succ = []
    shifts = Shift.objects.filter(norlonn_report__isnull=True, event__processed__isnull=False)

    if not shifts.exists():
        return HttpResponse("Nothing to generate!")

    if NorlonnReport.objects.filter(date=timezone.now()).exists():
        return HttpResponse("Already exists!")

    report = NorlonnReport(date=timezone.now())
    report.save()

    for s in shifts:
        if s.worker.norlonn_number is None:
            errors.append(_("ERR: %s - %s --- Lacks norlonn number" % (s.worker, s.event)))
            continue

        if not s.event.invoice.paid:
            errors.append(_("ERR: %s - %s --- Invoice not paid" % (s.worker, s.event)))
            continue

        succ.append(_("OK: %s - %s" % (s.worker, s.event)))
        s.norlonn_report = report
        s.save()

    if len(succ) == 0:
        report.delete()
        return HttpResponse(_("Nothing to generate!"))

    return render(request, 'norlonn/report.jinja', {'errors': errors, 'success': succ})


@login_required
@permission_required('norlonn.view_report')
def get_report(request, date):
    nr = get_object_or_404(NorlonnReport, date=date)
    linjer = []
    personshift = {}

    shift = Shift.objects.filter(norlonn_report=nr)
    for s in shift:
        if s.worker.norlonn_number in personshift:
            personshift[s.worker.norlonn_number].append(s)
        else:
            personshift[s.worker.norlonn_number] = [s, ]

    for (nl, ss) in personshift.items():
        total = Decimal(0)

        for s in ss:
            total += s.hours * s.wage

        total = total * Decimal("100")
        total = total.quantize(Decimal("10"))
        linjer.append(";" + str(s.worker.norlonn_number) + ";H1;100;" + str(total) + ";")

    return HttpResponse("\n".join(linjer), content_type="text/plain; charset=utf-8")
