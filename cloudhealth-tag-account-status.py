#!/usr/bin/env python3

# cloudhealth-tag-account-status - github.com/ora
# This will pull all AWS accounts provisioned in CloudHealth and tag them with current AWS account status.
# Accounts found in CH, but not found in AWS will be marked as Deleted.

import os
import http.client
import json
import boto3
import time


## If getting API key via environment variable ##
#api_key = os.environ.get('cloudhealth_api_key')


## If using secrets manager ##
client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='CloudHealth')
database_secrets = json.loads(response['SecretString'])
api_key = (database_secrets['cloudhealth_api_key'])


if (api_key) is None:
    print ("API key is not set")
    quit()



def get_accounts(api_key):
    base_url = 'chapi.cloudhealthtech.com'
    query = '/api/search.json?api_version=2&name=AwsAccount&fields=owner_id,name,amazon_name,tags'
    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % api_key}
    connection = http.client.HTTPSConnection(base_url)
    connection.request('GET', query, headers = headers)
    response =  json.loads(connection.getresponse().read().decode())
    connection.close()
    return response


def update_tag(api_key, asset_id, asset_type, tag_key, tag_value):
        base_url = 'chapi.cloudhealthtech.com'
        query = '/v1/custom_tags'
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % api_key}
        data = ({
            "tag_groups": [
                {
                    "asset_type": asset_type,
                    "ids": [asset_id],
                    "tags": [
                        {
                            "key": tag_key,
                            "value": tag_value
                        }
                    ]
                }
            ]
            })
        body = json.dumps(data)
        connection = http.client.HTTPSConnection(base_url)
        connection.request('POST', url = query, body = body, headers = headers)
        response = json.loads(connection.getresponse().read().decode())
        connection.close()
        print("Response: ",response)
        return response['updates']


client = boto3.client('organizations')

for item in get_accounts(api_key):
    try:
        response = client.describe_account(AccountId=item['owner_id'])
    except:
        AwsStatus = "DELETED"
    else:
        AwsStatus = response['Account']['Status']

    print ("\n\n\nId: ", item['owner_id'], "\nName: ", item['amazon_name'], "\nTags:", item['tags'], "\nStatus: ", AwsStatus)
    update_tag(api_key,item['id'],'AwsAccount','AwsStatus',AwsStatus)
    time.sleep(0.6)
