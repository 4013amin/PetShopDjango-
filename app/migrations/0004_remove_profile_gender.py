# Generated by Django 5.1.7 on 2025-04-13 10:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_chatmessage_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='gender',
        ),
    ]
