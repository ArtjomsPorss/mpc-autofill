# Generated by Django 3.2.4 on 2021-08-22 02:29

import datetime

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("cardpicker", "0017_auto_20210815_2107"),
    ]

    operations = [
        migrations.CreateModel(
            name="Blog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=20, unique=True)),
                ("url", models.CharField(max_length=10, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="BlogPost",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=40)),
                ("date_created", models.DateTimeField(default=datetime.datetime.now)),
                ("synopsis", models.TextField()),
                ("contents", models.TextField()),
                (
                    "blog",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="blog.blog"
                    ),
                ),
            ],
            options={
                "ordering": ["-date_created"],
            },
        ),
        migrations.CreateModel(
            name="ShowcaseBlogPost",
            fields=[
                (
                    "blogpost_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="blog.blogpost",
                    ),
                ),
                ("cards", models.ManyToManyField(to="cardpicker.Card")),
            ],
            bases=("blog.blogpost",),
        ),
    ]