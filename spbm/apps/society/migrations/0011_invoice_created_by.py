# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-03 22:19
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('society', '0010_auto_20170203_2319'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='created_by',
            field=models.ForeignKey(default=None, help_text='User which closed the period the invoice belongs to.',
                                    on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL,
                                    null=True),
        ),
    ]
