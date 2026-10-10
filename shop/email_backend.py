import ssl
from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend


class EmailBackend(DjangoSMTPBackend):
    """
    Same as Django's default SMTP backend, except the SSL context does NOT
    verify the certificate chain.

    Why this is needed:
    Some antivirus programs (Kaspersky, McAfee, etc.) or college/office
    networks intercept HTTPS/SMTP traffic and replace the certificate with
    their own. That replacement certificate is often malformed, which makes
    Python 3.13's strict SSL verification reject it with:
    "certificate verify failed: Basic Constraints of CA cert not marked
    critical".

    Django's SMTP backend builds its SSL context lazily as a cached_property
    (django.core.mail.backends.smtp.EmailBackend.ssl_context), so we override
    that property directly instead of passing an __init__ argument.

    NOTE: This disables certificate verification for outgoing mail only.
    Fine for a college/local project; do NOT use this for a real production
    deployment sending mail over the open internet, since it removes
    protection against man-in-the-middle attacks.
    """

    @property
    def ssl_context(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context