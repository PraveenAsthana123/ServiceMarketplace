# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-08 21:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0026_auto_20160408_1345'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='description',
            field=models.TextField(),
        ),
    ]
