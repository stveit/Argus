# Generated by Django 2.2.13 on 2020-06-17 15:08

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aas_alert', '0002_rename_network_system_to_alert_source'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alert',
            name='alert_id',
            field=models.TextField(verbose_name='alert ID'),
        ),
        migrations.AlterField(
            model_name='alert',
            name='details_url',
            field=models.TextField(blank=True, validators=[django.core.validators.URLValidator], verbose_name='details URL'),
        ),
        migrations.AlterField(
            model_name='alert',
            name='ticket_url',
            field=models.TextField(blank=True, help_text='URL to existing ticket in a ticketing system.', validators=[django.core.validators.URLValidator], verbose_name='ticket URL'),
        ),
        migrations.AlterField(
            model_name='alertrelationtype',
            name='name',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='alertsource',
            name='name',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='object',
            name='name',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='object',
            name='object_id',
            field=models.TextField(blank=True, verbose_name='object ID'),
        ),
        migrations.AlterField(
            model_name='object',
            name='url',
            field=models.TextField(validators=[django.core.validators.URLValidator], verbose_name='URL'),
        ),
        migrations.AlterField(
            model_name='objecttype',
            name='name',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='parentobject',
            name='name',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='parentobject',
            name='parentobject_id',
            field=models.TextField(verbose_name='parent object ID'),
        ),
        migrations.AlterField(
            model_name='parentobject',
            name='url',
            field=models.TextField(blank=True, validators=[django.core.validators.URLValidator], verbose_name='URL'),
        ),
        migrations.AlterField(
            model_name='problemtype',
            name='name',
            field=models.TextField(),
        ),
    ]