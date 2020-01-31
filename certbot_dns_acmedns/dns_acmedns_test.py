"""Tests for certbot_dns_acmedns.dns_acmedns"""

import os
import unittest
import json

import mock
from requests.exceptions import HTTPError
from certbot.compat import filesystem

from certbot import errors
from certbot.plugins import dns_test_common
from certbot.plugins.dns_test_common import DOMAIN, KEY
from acme import challenges

from certbot.tests import util as test_util
import tempfile

ACMEDNS_REGISTRATION = { "something.acme.com": {
  "username": "eabcdb41-d89f-4580-826f-3e62e9755ef2",
  "password": "pbAXVjlIOE01xbut7YnAbkhMQIkcwoHO0ek2j4Q0",
  "fulldomain": "d420c923-bbd7-4056-ab64-c3ca54c9b3cf.auth.example.org",
  "subdomain": "d420c923-bbd7-4056-ab64-c3ca54c9b3cf",
  "allowfrom": []
}}

ACMEDNS_URL = 'http://127.0.0.1:14441'


class AuthenticatorTest(test_util.TempDirTestCase,
                        dns_test_common.BaseAuthenticatorTest):

    def setUp(self):
        from certbot_dns_acmedns.dns_acmedns import Authenticator

        super(AuthenticatorTest, self).setUp()

        self.reg_file = os.path.join(self.tempdir, 'acmedns-registration.json')
        with open(self.reg_file, 'w') as fp:
            json.dump(ACMEDNS_REGISTRATION, fp)
        filesystem.chmod(self.reg_file, 0o600)

        path = os.path.join(self.tempdir, 'certbot-acmedns-credentials.ini')

        dns_test_common.write(
            {"acmedns_api_url": ACMEDNS_URL,
             "acmedns_registration_file": self.reg_file},
             path
        )

        self.config = mock.MagicMock(acmedns_credentials=path,
                                     acmedns_propagation_seconds=0)  # don't wait during tests

        self.auth = Authenticator(self.config, "acmedns")

        self.mock_client = mock.MagicMock()
        # _get_acmedns_client | pylint: disable=protected-access
        self.auth._get_acmedns_client = mock.MagicMock(return_value=self.mock_client)

    def test_perform(self):
        self.auth.perform([self.achall])

        expected = [mock.call.add_txt_record("_acme-challenge." +
                                                DOMAIN, mock.ANY)]
        self.assertEqual(expected, self.mock_client.mock_calls)

    def test_cleanup(self):
        # _attempt_cleanup | pylint: disable=protected-access
        self.auth._attempt_cleanup = True
        self.auth.cleanup([self.achall])

        expected = [mock.call.del_txt_record("_acme-challenge." +
                                                DOMAIN)]
        self.assertEqual(expected, self.mock_client.mock_calls)

    def test_no_credentials(self):
        dns_test_common.write({}, self.config.acmedns_credentials)
        self.assertRaises(errors.PluginError,
                          self.auth.perform,
                          [self.achall])

    def test_missing_api_url(self):
        dns_test_common.write(
            {"acmedns_registration_file": self.reg_file},
             self.config.acmedns_credentials
        )

        self.assertRaises(errors.PluginError,
                          self.auth.perform,
                          [self.achall])

    def test_registration_file_path(self):
        dns_test_common.write(
            {"acmedns_registration_file": self.reg_file},
             self.config.acmedns_credentials
        )

        self.assertRaises(errors.PluginError,
                          self.auth.perform,
                          [self.achall])


class AcmeDNSClientTest(unittest.TestCase):

    TTL = 0

    def setUp(self):
        from certbot_dns_acmedns.dns_acmedns import _AcmeDNSClient

        self.fake_client = mock.MagicMock()

        self.ACMEDNS_REGISTRATION_FILE=tempfile.NamedTemporaryFile()
        with open(self.ACMEDNS_REGISTRATION_FILE.name, 'w') as fp:
            json.dump(ACMEDNS_REGISTRATION, fp)

        filesystem.chmod(self.ACMEDNS_REGISTRATION_FILE.name, 0o600)

        self.acmedns_client = _AcmeDNSClient(
            api_url=ACMEDNS_URL,
            credentials_file=self.ACMEDNS_REGISTRATION_FILE.name,
            ttl=self.TTL
        )

        self.acmedns_client.client = self.fake_client

    def tearDown(self):
        # Close the file, the directory will be removed after the test
        self.ACMEDNS_REGISTRATION_FILE.close()

    def test_add_txt_record(self):
        self.assertEqual(self.acmedns_client.add_txt_record('_acme-challenge.something.acme.com', mock.ANY), None)

    def test_del_txt_record(self):
        self.assertEqual(self.acmedns_client.del_txt_record('_acme-challenge.something.acme.com'), None)

    def test_missing_credentials(self):
        self.assertRaises(errors.PluginError,
                          self.acmedns_client.add_txt_record,
                          '_acme-challenge.anotherdomain.acme.com',mock.ANY)

    def test_missing_domain_in_registration(self):
        MISSING_DOMAIN = {
        "username": "eabcdb41-d89f-4580-826f-3e62e9755ef2",
        "password": "pbAXVjlIOE01xbut7YnAbkhMQIkcwoHO0ek2j4Q0",
        "fulldomain": "d420c923-bbd7-4056-ab64-c3ca54c9b3cf.auth.example.org",
        "subdomain": "d420c923-bbd7-4056-ab64-c3ca54c9b3cf",
        "allowfrom": []
        }
        with open(self.ACMEDNS_REGISTRATION_FILE.name, 'w+') as fp:
            json.dump(MISSING_DOMAIN, fp)

        self.assertRaises(errors.PluginError,
                          self.acmedns_client.add_txt_record,
                          "mock.ANY", mock.ANY)


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
