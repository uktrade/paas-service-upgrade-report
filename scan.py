#!/usr/bin/env python

import os
import datetime as dt
import json

from cloudfoundry_client.client import CloudFoundryClient
import requests

SLACK_URL = os.environ["SLACK_URL"]
SLACK_CHANNEL = os.environ["SLACK_CHANNEL"]


def send_slack_message(text):
    response = requests.post(SLACK_URL, json.dumps({
        "channel": SLACK_CHANNEL,
        "username": "upgradebot",
        "text": text,
        "icon_emoji": ":ghost:"
    }))


def scan(client):
    redis_list = []
    postgres_list = []

    for org in client.v2.organizations:
        for space in org.spaces():

            for app in space.apps():

                for sb in app.service_bindings():
                    service = sb.service_instance()
                    name = service["entity"]["name"]

                    if service["entity"]["type"] != "user_provided_service_instance" and "autoscaler" not in service["entity"]["name"]:

                        try:
                            plan = service.service_plan()
                        except:
                            continue

                        if "Postgres" not in plan["entity"]["description"] and "S3" not in plan["entity"]["description"] and plan["entity"]["name"][-1] != "1" and "5" not in plan["entity"]["name"] and "6" not in plan["entity"]["name"]:
                            binding_count = service.service_bindings().total_results

                            bound_text = "UNBOUND" if not binding_count else ""
                            redis_list.append("{}/{}/{} - {} {}".format(
                                org["entity"]["name"],
                                space["entity"]["name"],
                                service["entity"]["name"],
                                plan["entity"]["name"],
                                bound_text,
                            ))

                        if "Postgres Version 10" in plan["entity"]["description"] or "Postgres Version 11" in plan["entity"]["description"]:
                            binding_count = service.service_bindings().total_results

                            bound_text = "UNBOUND" if not binding_count else ""
                            postgres_list.append("{}/{}/{} - {} {}".format(
                                org["entity"]["name"],
                                space["entity"]["name"],
                                service["entity"]["name"],
                                plan["entity"]["name"],
                                bound_text,
                            ))
    return postgres_list, redis_list



if __name__ == '__main__':

    proxy = dict(http=os.environ.get('HTTP_PROXY', ''), https=os.environ.get('HTTPS_PROXY', ''))

    if os.environ.get("CF_USERNAME"):
        client = CloudFoundryClient(target_endpoint=os.environ["CF_DOMAIN"])
        client.init_with_user_credentials(os.environ["CF_USERNAME"], os.environ["CF_PASSWORD"])
    else:
        # Run using cf cli auth
        client = CloudFoundryClient.build_from_cf_config()

    is_weekday = dt.date.today().weekday() < 5

    if is_weekday:
        print("Performing scan ...")

        postgres_list, redis_list = scan(client)
        postgres_list.append("Total: {}".format(len(postgres_list)))
        redis_list.append("Total: {}".format(len(redis_list)))

        redis_text = "Redis instance report\n\n" + "\n".join(redis_list)
        postgres_text = "Postgres instance report\n\n" + "\n".join(postgres_list)

        send_slack_message(redis_text)
        send_slack_message(postgres_text)

        print("Scan complete ...")
