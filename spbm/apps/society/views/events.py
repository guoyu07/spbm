from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.forms.formsets import formset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView
from extra_views import CreateWithInlinesView

from helpers.mixins import LoggedInPermissionsMixin
from spbm.helpers.auth import user_allowed_society
from ..forms.events import EventForm, make_shift_base, InlineShiftForm
from ..models import Society, Event, Shift


@login_required
def index(request, society_name=None):
    society = request.user.spfuser.society if society_name is None \
        else get_object_or_404(Society, shortname=society_name)

    if not user_allowed_society(request.user, society):
        return render(request, "errors/unauthorized.jinja")

    events = Event.objects.filter(society=society)
    processed = events.values('processed').distinct().extra(select={'processed_is_null': 'processed IS NULL'},
                                                            order_by=['-processed_is_null', '-processed'])
    events_by_date = {}
    for event in processed:
        events_by_date[event['processed']] = events.filter(processed=event['processed']).order_by('-date')

    return render(request, "events/index.jinja",
                  {'processed': processed, 'events': events_by_date, 'cur_page': 'events'})


class EventAddView(LoginRequiredMixin, CreateWithInlinesView):
    template_name = "events/add.jinja"
    model = Event
    fields = ['name', 'date']
    inlines = [InlineShiftForm]


class EventAddViewPlain(LoggedInPermissionsMixin, CreateView):
    template_name = "events/add.jinja"
    # Following only relevant to extra_views
    model = Event
    inlines = [InlineShiftForm]
    fields = ['name', 'date']

    _society = None
    _user = None

    def has_permission(self):
        return user_allowed_society(self._user, self._society)

    def dispatch(self, request, *args, **kwargs):
        self._society = request.user.spfuser.society if 'society_name' not in kwargs \
            else get_object_or_404(Society, shortname=kwargs['society_name'])
        self._user = request.user
        return super(EventAddView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        event_form = EventForm(prefix='event')
        shift_formset = formset_factory(make_shift_base(self._society), min_num=6, max_num=12)(
            prefix='shift')
        # return super(EventAddView, self).get(request, *args, **kwargs)
        return render(request, "events/add.jinja", {'form': event_form,
                                                    'inlines': [shift_formset]})

    def post(self, request, *args, **kwargs):
        event_form = EventForm(request.POST, prefix="event")
        shift_formset = formset_factory(make_shift_base(self._society), min_num=6, max_num=12)(
            request.POST, prefix='shift')
        if event_form.is_valid():
            with transaction.atomic():
                event = event_form.save(commit=False)
                event.society = self._society
                event.save()

                for shift in shift_formset:
                    if not shift.is_valid():
                        continue

                    if "worker" not in shift.cleaned_data:
                        continue

                    print(shift.cleaned_data['worker'])
                    db_shift = Shift()
                    db_shift.event = event
                    db_shift.worker = shift.cleaned_data['worker']
                    db_shift.wage = shift.cleaned_data['wage']
                    db_shift.hours = shift.cleaned_data['hours']
                    db_shift.save()
                return redirect(index)
        else:
            return render(request, "events/add.jinja", {'form': event_form,
                                                        'inlines': [shift_formset]})


@login_required
def add(request, society_name=None):
    society = request.user.spfuser.society if society_name is None \
        else get_object_or_404(Society, shortname=society_name)

    if not user_allowed_society(request.user, society):
        return render(request, "errors/unauthorized.jinja")

    event_form = EventForm
    shift_form = formset_factory(make_shift_base(society), min_num=6, max_num=12)

    if request.method == "POST":
        event_formset = event_form(request.POST, prefix="event")
        shift_formset = shift_form(request.POST, prefix="shift")

        if event_formset.is_valid():
            with transaction.atomic():
                event = event_formset[0].save(commit=False)
                event.society = society
                event.save()

                for shift in shift_formset:
                    if not shift.is_valid():
                        continue

                    if "worker" not in shift.cleaned_data:
                        continue

                    print(shift.cleaned_data['worker'])
                    db_shift = Shift()
                    db_shift.event = event
                    db_shift.worker = shift.cleaned_data['worker']
                    db_shift.wage = shift.cleaned_data['wage']
                    db_shift.hours = shift.cleaned_data['hours']
                    db_shift.save()
                return redirect(index)
    else:
        event_formset = event_form(prefix="event")
        shift_formset = shift_form(prefix="shift")

    return render(request, "events/add.jinja", {'event_formset': event_formset, 'shift_formset': shift_formset})
