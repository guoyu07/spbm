from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView

from spbm.helpers.auth import user_allowed_society, user_society


@login_required
def index(request):
    society = request.user.spfuser.society
    if not user_allowed_society(request.user, society):
        return render(request, "errors/unauthorized.jinja")

    return render(request, "index.jinja",
                  {'society': society, 'cur_page': 'society'})


class Overview(LoginRequiredMixin, TemplateView):
    template_name = 'index.jinja'

    def get_context_data(self, request, **kwargs):
        society = user_society(request.user)
        context = super().get_context_data(**kwargs)
        context.update({
            'society': society,
        })

        return context
