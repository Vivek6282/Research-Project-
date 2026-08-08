"""
Trackside — Accounts app configuration.

Registers the accounts app with Django. This app handles authentication,
user management, and role-based permissions for the entire platform.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Accounts & Authentication"
