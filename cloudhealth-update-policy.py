#!/usr/bin/env python3

# cloudhealth-update-policy - SecOps - olegr
# Updates accounts missing arn:aws:iam::x:role/CloudHealth in assume_role_arn, which all new accounts do.
# CH will not pull data from account until the role is manually specified.

import os
import http.client
import json
import time
import boto3

# If getting API key via environment variable

# api_key = os.environ.get('cloudhealth_api_key')
# ch_external_id = os.environ.get('cloudhealth_external_id')


client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='CloudHealth')
database_secrets = json.loads(response['SecretString'])
api_key = (database_secrets['cloudhealth_api_key'])
ch_external_id = (database_secrets['cloudhealth_external_id'])


if (api_key) is None:
    print ("API key is not set")
    quit()


def get_accounts(api_key):
    base_url = 'chapi.cloudhealthtech.com'
    query = '/api/search.json?api_version=2&name=AwsAccount&fields=owner_id,amazon_name,name,assume_role_arn,assume_role_external_id'
    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % api_key}
    connection = http.client.HTTPSConnection(base_url)
    connection.request('GET', query, headers = headers)
    response =  json.loads(connection.getresponse().read().decode())
    connection.close()
    return response

def update_account(api_key, ch_account_id, role_arn, aws_id, external_id):

    client = boto3.client('organizations')
    response = client.describe_account(AccountId=aws_id)
    AwsName = response['Account']['Name']

    base_url = 'chapi.cloudhealthtech.com'
    query = '/v1/aws_accounts/%s' % ch_account_id
    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % api_key}
    account_info = {
       "name": "%s" % AwsName,
        "authentication": {
            "protocol": "assume_role",
            "assume_role_arn": "%s" % role_arn,
            "assume_role_external_id": "%s" % external_id
            }
        }
    body = json.dumps(account_info)
    connection = http.client.HTTPSConnection(base_url)
    connection.request('PUT', url = query, body = body, headers = headers)
    response =  connection.getresponse()
    print(json.loads(response.read().decode()))
    connection.close()
    return response



for item in get_accounts(api_key):
    print ("\n\nId:", item['id'], "\nAwsID:", item['owner_id'], "\nPolicyArn:", item['assume_role_arn'], "\nExternal Id:",item['assume_role_external_id'])
    if item['owner_id'] is None:
        print ("🚨 Blank AWS Id")
        continue
    RoleArn = "arn:aws:iam::" + item['owner_id'] + ":role/CloudHealth"
    if item['assume_role_arn'] == RoleArn:
        print ("👍")
    else:
        print ("🚨 Updating Name, Role, and ExternalId\n")
        update_account(api_key, item['id'],RoleArn,item['owner_id'],ch_external_id)
    time.sleep(0.5)
