"""DNS Authenticator for ACME-DNS."""

import json
import logging

import zope.interface
from certbot import interfaces
from certbot import errors

from certbot.plugins import dns_common

from pyacmedns import Client, Storage



logger = logging.getLogger(__name__)

@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for ACME-DNS DNS."""

    description = 'Obtain certificates using a DNS TXT record ' + \
                  '(if you are using ACME-DNS for DNS.)'

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None
        self.ttl = 60

    @classmethod
    def add_parser_arguments(cls, add): # pylint: disable=arguments-differ
        super(Authenticator, cls).add_parser_arguments(add)
        add('credentials', help='ACMEDNS Certbot credentials INI file.')

    def more_info(self):  # pylint: disable=missing-docstring,no-self-use
        return 'This plugin configures a DNS TXT record to respond to a dns-01 challenge using ' + \
                'ACME-DNS API'

    def _validate_credentials(self, credentials):
        if not credentials.conf('api-url'):
            raise errors.PluginError('{0}: ACME-DNS API URL not provided.'
                                        .format(self.conf('credentials')))
        try:
            dns_common.validate_file_permissions(credentials.conf('registration-file'))
        except TypeError:
            raise errors.PluginError('Path invalid or file not found.')

    def _setup_credentials(self):
        self._configure_file('credentials',
                             'Absolute path to ACME-DNS credentials file')

        dns_common.validate_file_permissions(self.conf('credentials'))

        self.credentials = self._configure_credentials(
            'credentials',
            'ACME-DNS Certbot credentials file',
            {
                'api-url': 'ACME-DNS-compatible API URL',
                'registration-file': 'JSON file containing ACME-DNS registrations'
            }
        )

        self.credentials = self._configure_credentials('credentials',
                             'Absolute path to ACME-DNS credentials file',
                             None,
                             self._validate_credentials)

    def _perform(self, domain, validation_name, validation):
        self._get_acmedns_client().add_txt_record(validation_name, validation)

    def _cleanup(self, domain, validation_name, validation):
        self._get_acmedns_client().del_txt_record(validation_name)

    def _get_acmedns_client(self):
        return _AcmeDNSClient(
            api_url=self.credentials.conf('api-url'),
            credentials_file=self.credentials.conf('registration-file'),
            ttl=self.ttl
        )

class _AcmeDNSClient(object):
    """
    Encapsulates all communication with the ACME-DNS server.
    """

    def __init__(self, api_url, credentials_file, ttl):
        super(_AcmeDNSClient, self).__init__()

        self.credentials_file = credentials_file
        self.ttl = ttl
        self.client = Client(api_url)
        self.account = None

    def add_txt_record(self, record_name, record_content): # pylint: disable=missing-docstring
        self._load_credentials(self._get_domain(record_name))
        self.client.update_txt_record(self.account, record_content)

    def del_txt_record(self, record_name): # pylint: disable=missing-docstring, unused-argument
        return

    def _get_domain(self, validation_name):
        ACME_CHALLENGE_PREFIX = "_acme-challenge."
        if isinstance(validation_name, str):
            if validation_name.startswith(ACME_CHALLENGE_PREFIX):
                return validation_name[len(ACME_CHALLENGE_PREFIX):]
        return ""

    def _validate_registration_file(self):
        # registration_file here is the JSON file containing as key the domain
        # and as value the response returned during ACME-DNS registration
        # {
        #     "something.acme.com": {
        #         "username": "eabcdb41-d89f-4580-826f-3e62e9755ef2",
        #         "password": "pbAXVjlIOE01xbut7YnAbkhMQIkcwoHO0ek2j4Q0",
        #         "fulldomain": "d420c923-bbd7-4056-ab64-c3ca54c9b3cf.auth.example.org",
        #         "subdomain": "d420c923-bbd7-4056-ab64-c3ca54c9b3cf",
        #         "allowfrom": []
        #     },
        #     "foo.bar.com": {
        #         "username": "64570f82-d5ca-4839-8306-c4e392d8ae82",
        #         "password": "bkhMQIkcwoHO0ek2j4Q0pbAXVjlIOE01xbut7YnA",
        #         "fulldomain": "179adbde-4a06-4f47-af17-1c250106fb9f.auth.example.org",
        #         "subdomain": "179adbde-4a06-4f47-af17-1c250106fb9f",
        #         "allowfrom": []
        #     }
        # }
        try:
            with open(self.credentials_file) as json_file:
                try:
                    credentials_data = json.load(json_file)
                    if len(credentials_data.keys()) == 0:
                        raise errors.PluginError('{}: ACME-DNS registration file is empty?'
                                                    .format(self.credentials_file))

                    cred_items = ['username', 'password', 'fulldomain', 'subdomain', 'allowfrom']
                    for i in credentials_data.keys():
                        if i in cred_items:
                            raise errors.PluginError('{}: appears to not contain domain as key. '
                                                    'Make sure the JSON is a dictionary and each '
                                                    'where the key is the domain and the value is '
                                                    'the ACME-DNS registration returned for that '
													'domain.'
                                                    .format(self.credentials_file))
                except json.JSONDecodeError:
                    raise errors.PluginError('{}: unable to parse json file. Make '
                                                    'sure it\'s a valid json file'
                                                    .format(self.credentials_file))
        except IOError as e:
            raise errors.PluginError('{}: I/O error'
                                        .format(self.credentials_file))
        except: #handle other exceptions such as attribute errors
            raise errors.PluginError('{}: Unexpected error while opening file.'
                                        .format(self.credentials_file))

    def _load_credentials(self, domain):
        storage = Storage(self.credentials_file)

        self.account = storage.fetch(domain)

        if not self.account:
            raise errors.PluginError('Unable to find a domain in ' +
                                        self.credentials_file + ' matching "' +
                                        domain + '"')
