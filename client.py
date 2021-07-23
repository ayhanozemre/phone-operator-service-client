import os
import sys
import json
import logging
from itertools import chain

import asyncio
import requests
from fake_useragent import UserAgent


ua = UserAgent(cache=True)
logger = logging.getLogger(__name__)

OPERATOR_DOMAIN = os.environ.get('OPERATOR_DOMAIN')
if not OPERATOR_DOMAIN:
    logger.error('[**] OPERATOR_DOMAIN not defined')
    sys.exit(1)

BASE_URL = 'https://{domain}'.format(domain=OPERATOR_DOMAIN)
API_URL = os.path.join(BASE_URL, 'clicktodoor-api/api/v1')


AVAILABLE_STATUS = ('LOCKED', 'AVAILABLE')


def is_available(item):
    return item.get('msisdnStatus') in AVAILABLE_STATUS


def make_request(endpoint, method='get', data=None, headers=None):
    if not headers:
        headers = {}
    headers.update({'User-Agent': ua.random})
    url = os.path.join(API_URL, endpoint)
    return requests.request(method, url, data=data, headers=headers)


def prepare_request(*args, **kwargs):
    req = make_request(*args, **kwargs)
    response = {}
    if req.ok:
        response = req.json()
    else:
        logger.warning('response is not json serializable')
    return response


def send_sms(number):
    return prepare_request('sendSms/{}/true'.format(number))


def sms_code_verify(code, number):
    payload = {
        'msisdn': number,
        'sendCode': code,
        'candidateType': 'NEW',
        'isPbmOk': True,
        'selectedAddon': None,
        'tariffId': 152,
        'sourceId': ''}
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
    }
    return prepare_request('controlOtpSms',
                           method='post',
                           data=json.dumps(payload),
                           headers=headers)


def get_number_detail(id):
    return prepare_request('msisdns/%s' % id)


def available_random_numbers():
    return prepare_request('msisdns/available')


def find_number(number, items):
    return filter(lambda x: number in x['number'], items)


def find_available_number(number, loop_count=1):
    async def find_available_numbers(number):
        items = available_random_numbers()
        return find_number(number, items)

    number = str(number)
    loop = asyncio.get_event_loop()
    tasks = asyncio.gather(*[
        find_available_numbers(number)
        for i in range(0, loop_count)])
    loop.run_until_complete(tasks)
    return list(chain(*tasks.result()))
