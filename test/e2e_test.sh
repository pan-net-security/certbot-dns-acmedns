#!/bin/sh

TEMP_DIR=$(mktemp -d 2>/dev/null || echo '/tmp/'$(date +%Y-%m-%d-%H-%M-%S)  )
OUTPUT_FILE="$TEMP_DIR/output"
export PYTHONWARNINGS="ignore:Unverified HTTPS request"

CREDENTIALS_FILE_PATH="$TEMP_DIR/credentials.ini"


## Step 1 - Define the FQDN(s) certificates must be issued
TEST_FQDN="something.acme.com"
curl -s -X PATCH http://pdns:8081/api/v1/servers/localhost/zones/acme.com. \
-d '{"rrsets": [ {"name": "'$TEST_FQDN'.", "type": "A", "ttl": 30, "changetype": "REPLACE", "records": [ {"content": "127.0.0.50", "disabled": false } ] } ] }' \
-H "X-API-Key: secret"

## Step 2 - Register in ACME-DNS and write the JSON file
# The file should look like this:
# {
#   "something.acme.com": {
#     "username": "2db9cee2-0af7-4725-9b02-ba575a2f839f",
#     "password": "i4OWCMMoCAcbv3sbsaX5_w0OM_SQpyMG2ZeRsuAM",
#     "fulldomain": "76d61ca7-70aa-4cc8-8f2f-347bd9b32ca4.auth.example.org",
#     "subdomain": "76d61ca7-70aa-4cc8-8f2f-347bd9b32ca4",
#     "allowfrom": []
#   }
# }

ACME_REGISTRATION_FILE="$TEMP_DIR/acme-registration.json"
echo '{}' | jq  --arg domain $TEST_FQDN \
                --argjson creds \
                "$(curl -s -k -X POST  http://acmedns/register)" '.[$domain] += $creds' \
                > $ACME_REGISTRATION_FILE

## Step 3 - Setup the CNAME for the FQDN
# grab full domain from registration
ACMEDNS_FULLDOMAIN=$(jq -r --arg fqdn $TEST_FQDN '.[$fqdn].fulldomain' $ACME_REGISTRATION_FILE)"."

# crete _acme-challenge CNAME for the FQDN
curl -s -X PATCH http://pdns:8081/api/v1/servers/localhost/zones/acme.com. \
-d '{"rrsets": [ {"name": "_acme-challenge.'$TEST_FQDN'.", "type": "CNAME", "ttl": 30, "changetype": "REPLACE", "records": [ {"content": "'$ACMEDNS_FULLDOMAIN'", "disabled": false } ] } ] }' \
-H "X-API-Key: secret"

# give some quick for propagation
sleep 5

# verify the CNAME is resolving and correct
DIG_RESULT=$(dig +short _acme-challenge.$TEST_FQDN CNAME)

if [ "$ACMEDNS_FULLDOMAIN" = "$DIG_RESULT" ]; then
    echo "CNAME set and matches the ACME-DNS fulldomain, continuing.."
else
    echo "CNAME for _acme-challenge."$TEST_FQDN" should be set and matching to "$ACMEDNS_FULLDOMAIN
fi

# Step 4 - Configure ACME-DNS Certbot ini file and set permissions
echo 'certbot_dns_acmedns:dns_acmedns_api_url = http://acmedns' > $CREDENTIALS_FILE_PATH
echo "certbot_dns_acmedns:dns_acmedns_registration_file = $ACME_REGISTRATION_FILE" >> $CREDENTIALS_FILE_PATH
chmod 0600 $CREDENTIALS_FILE_PATH
chmod 0600 $ACME_REGISTRATION_FILE

echo "# Logs, certificates, keys, accounts will be contained in '$TEMP_DIR'"

mkdir -p $TEMP_DIR/var/log/letsencrypt \
        $TEMP_DIR/etc/letsencrypt \
        $TEMP_DIR/var/lib/letsencrypt

chmod -R 0755 $TEMP_DIR/var/log/letsencrypt \
              $TEMP_DIR/etc/letsencrypt \
              $TEMP_DIR/var/lib/letsencrypt


# Step 4 - Request the certificate
certbot \
        --certbot-dns-acmedns:dns-acmedns-credentials $CREDENTIALS_FILE_PATH \
        --certbot-dns-acmedns:dns-acmedns-propagation-seconds 5 \
        --authenticator certbot-dns-acmedns:dns-acmedns \
        --logs-dir $TEMP_DIR/var/log/letsencrypt/ \
        --server https://pebble:14000/dir \
        --work-dir $TEMP_DIR/var/lib/letsencrypt \
        --config-dir $TEMP_DIR/etc/letsencrypt \
        --domains $TEST_FQDN \
        --email admin@TEST_FQDN \
        --non-interactive \
        --no-verify-ssl  \
        --agree-tos \
        --debug \
        certonly | tee -a $OUTPUT_FILE

echo "# Files created in '$TEMP_DIR': "
find ${TEMP_DIR:-/tmp}/

set -e
grep -qi 'CONGRATULATIONS' $OUTPUT_FILE