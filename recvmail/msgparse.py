import re
from email import policy
from email.header import decode_header, make_header
from email.parser import Parser
from email.utils import parseaddr, formataddr

from sh8core.models import Mail

CHARSET_IN_CONTENTTYPE_REGEX = re.compile(r'charset="*([\w-]+)"*')


def raw_to_mail(rawtext):
    msg = Parser(policy=policy.default).parsestr(rawtext)

    sender = readablize_header(msg.get('From'))
    subject = readablize_header(msg.get('Subject'))

    address = Address(header_to=msg.get('To'))

    body = msg.get_body(preferencelist=('html', 'plain'))
    _try_set_charset_smarter(body)

    contents = str(body.get_payload(decode=True),
                   encoding=str(body.get_charset()))
    content_type = body.get_content_type()

    mail = Mail(recipient=address.recipient,
                secret_code=address.secret_code,
                sender=sender,
                subject=subject,
                contents=contents,
                content_type=content_type,)

    return mail


def _try_set_charset_smarter(body):
    if body.get_charset() is None:
        content_type = body['Content-Type']
        if content_type and 'charset=' in content_type:
            charset = CHARSET_IN_CONTENTTYPE_REGEX.search(content_type).group(1)
        else:
            charset = 'utf-8'  # Use default charset.
        body.set_charset(charset)


def readablize_header(header):
    return str(make_header(decode_header(header)))


def reproduce_mail(origin, rcpttos):
    mails = []
    for rcptto in rcpttos:
        address = Address(header_to=rcptto)
        m = Mail(
                recipient=address.recipient,
                secret_code=address.secret_code,
                sender=origin.sender,
                subject=origin.subject,
                contents=origin.contents,
        )
        mails.append(m)
    return mails


class Address(object):
    """
    Address consist of local, domain, name.

    When we have a mail account "mike@home.com", and it's presented as "Miky <mike@home.com>" on 'To' message header,
      - local is 'mike',
      - domain is 'home.com',
      - name is 'Miky'.
    **Summarize - an address form**
      - name <local@domain>
    The local consist of recipient and secret_code.
      - name <recipient__secret_code@domain>
    """
    secret_code_sep = '__'

    def __init__(self, local=None, domain=None, name='Name', header_to=None):
        self.local = local
        self.domain = domain
        self.name = name

        if header_to:
            self.name, address_str = parseaddr(header_to)
            self.local, self.domain = address_str.split('@')

    @property
    def recipient(self):
        return self._split_local()[0]

    @property
    def secret_code(self):
        return self._split_local()[1]

    def _split_local(self):
        if self._is_secret(self.local):
            recipient, secret_code = self.local.split(self.secret_code_sep)
            return recipient, secret_code
        else:
            return self.local, None

    def _is_secret(self, local):
        return self.secret_code_sep in local

    def as_str(self):
        return self.local + '@' + self.domain

    def as_headerstr(self):
        return formataddr((self.name, self.as_str()))

    def __str__(self):
        return self.as_str()
