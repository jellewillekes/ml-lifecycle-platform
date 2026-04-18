"""Hosted CI helpers — maintainer-only verification code for GCP staging.

These modules are not part of the local contributor surface. They support
hosted GitHub Actions workflows, operator scripts under ``scripts/verify_*``,
and the maintenance jobs in ``ml_lifecycle_platform.jobs``. A normal local
PR does not need to import or run any of this code.
"""
