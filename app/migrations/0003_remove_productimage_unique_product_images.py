# Generated by Django 5.1.4 on 2025-01-07 15:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_alter_product_image'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='productimage',
            name='unique_product_images',
        ),
    ]
