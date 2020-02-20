[![Build Status](https://travis-ci.com/pan-net-security/certbot-dns-acmedns.svg?branch=master)](https://travis-ci.com/pan-net-security/certbot-dns-acmedns)
[![Coverage Status](https://coveralls.io/repos/github/pan-net-security/certbot-dns-acmedns/badge.svg?branch=master)](https://coveralls.io/github/pan-net-security/certbot-dns-acmedns?branch=master)
![Libraries.io dependency status for latest release](https://img.shields.io/librariesio/release/github/pan-net-security/certbot-dns-acmedns.svg)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=pan-net-security_certbot-dns-acmedns&metric=alert_status)](https://sonarcloud.io/dashboard?id=pan-net-security_certbot-dns-acmedns)
![PyPI - Status](https://img.shields.io/pypi/status/certbot-dns-acmedns.svg)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/certbot-dns-acmedns.svg)


certbot-dns-acmedns
============

ACME-DNS DNS Authenticator plugin for [Certbot](https://certbot.eff.org/).

ACME-DNS is a simplified DNS server with a RESTful HTTP API to provide a simple way to automate ACME DNS challenges. Explaining details of ACME-DNS is not part of this repo, we assume you have running ACME-DNS server. To understand what ACME-DNS is and for details on how to run/use ACME-DNS server see [ACME-DNS repo.](https://github.com/joohoi/acme-dns)

This plugin is built from the ground up and follows the development style and life-cycle
of other `certbot-dns-*` plugins found in the individual directories of the
[Official Certbot Repository](https://github.com/certbot/certbot).

For general information about Certbot plugin development see [Certbot developer documentation.](https://certbot.eff.org/docs/contributing.html#plugin-architecture)


Installation
------------

```
pip install --upgrade certbot
pip install certbot-dns-acmedns
```

Verify:

```
$ certbot plugins --text

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
* certbot-dns-acmedns:dns-acmedns
Description: Obtain certificates using a DNS TXT record (if you are using
ACME-DNS for DNS.)
Interfaces: IAuthenticator, IPlugin
Entry point: dns-acmedns = certbot_dns_acmedns.dns_acmedns:Authenticator

...
...
```

Configuration
-------------

The (certbot) credentials file e.g. `acmedns-credentials.ini` should look like this:

```
# cat acmedns-credentials.ini
certbot_dns_acmedns:dns_acmedns_api_url = http://acmedns-server/
certbot_dns_acmedns:dns_acmedns_registration_file = /etc/certbot/acme-registration.json
```

This plugin **does not do ACME-DNS registration** and you are responsible to make
sure `/etc/certbot/acme-registration.json` (in the example above) contains
the registration data in the following format:

```
# cat /etc/certbot/acme-registration.json
{
  "something.acme.com": {
    "username": "6e14735c-2c6a-447e-b63d-a23ac4438bd7",
    "password": "dd6gnYS-IxrQfDLbdPRX3hrFhS_SLrwbS0kSl_i8",
    "fulldomain": "3b750a0e-c627-423f-9966-4799c6a9533b.auth.example.org",
    "subdomain": "3b750a0e-c627-423f-9966-4799c6a9533b",
    "allowfrom": []
  }
}
```

This format is the same as the one used in some other tools, e.g.
[cert-manager ACME-DNS plugin](https://cert-manager.io/docs/configuration/acme/dns01/acme-dns/)

Usage
-----


```
certbot ... \
        --authenticator certbot-dns-acmedns:dns-acmedns  \
        --certbot-dns-acmedns:dns-acmedns-credentials /etc/certbot/acmedns-credentials.ini \
        certonly
```

FAQ
-----

##### Why such long name for a plugin?

This follows the upstream nomenclature: `certbot-dns-<dns-provider>`.

##### Why do I have to use `:` separator in the name? And why are the configuration file parameters so weird?

This is a limitation of the Certbot interface towards _third-party_ plugins.

For details read the discussions:

- https://github.com/certbot/certbot/issues/6504#issuecomment-473462138
- https://github.com/certbot/certbot/issues/6040
- https://github.com/certbot/certbot/issues/4351
- https://github.com/certbot/certbot/pull/6372

Development
-----------

Create a virtualenv, install the plugin (`editable` mode),
spawn the environment and run the test:

### Prepare the support environment:
```
docker-compose up -d
```

You can also omit `-d` if you wish to see backend server logs side-by-side with
the client.

### Run certbot client
```
docker build -t certbot_acmedns_client -f test/Dockerfile test/
docker run -it --rm --network certbot-dns-acmedns_default --dns "10.151.40.100" -v $PWD:/certbot-dns-acmedns certbot_acmedns_client sh -c 'pip3 install -e /certbot-dns-acmedns && /certbot-dns-acmedns/test/e2e_test.sh'
```


License
--------

Apache License Version 2.0, January 2004


Authors
-------

[DT Pan-Net s.r.o](https://github.com/pan-net-security)
