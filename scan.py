#!/usr/bin/env python

import csv
import datetime as dt
import json
import os

import requests
from cloudfoundry_client.client import CloudFoundryClient

SLACK_URL = os.environ["SLACK_URL"]
SLACK_CHANNEL = os.environ["SLACK_CHANNEL"]
SCAN_POSTGRES = os.getenv("SCAN_POSTGRES", "False").lower() in ("true", "yes", "y")
SCAN_REDIS = os.getenv("SCAN_REDIS", "False").lower() in ("true", "yes", "y")
SCAN_CFLINUX = os.getenv("SCAN_CFLINUX", "False").lower() in ("true", "yes", "y")
GENERATE_CSV = os.getenv("GENERATE_CSV", "False").lower() in ("true", "yes", "y")


def send_slack_message(header, data):
    slack_message = []
    section_text = f"```"

    data_size = len(data)
    while data:
        while len(section_text) < 2920 and data:
            content = data.pop()
            section_text += (
                f"{content[0]}/{content[1]}/{content[2]} {' '.join(content[3:])}"
            )
            section_text += "\n"

        section_text += "```"
        slack_message.append(
            {"type": "header", "text": {"type": "plain_text", "text": header}}
        )
        slack_message.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": section_text.strip()},
            }
        )

        header = "-"
        section_text = "```"

    # append total at the bottom
    slack_message.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```Total:{data_size}```"},
        }
    )

    payload = json.dumps(
        {
            "channel": SLACK_CHANNEL,
            "username": "upgradebot",
            "blocks": slack_message,
            "icon_emoji": ":ghost:",
        }
    )

    response = requests.post(
        SLACK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        timeout=90,
    )


def _scan_cflinuxfs(client):
    cflinux_list = []
    for org in client.v2.organizations:
        for space in org.spaces():
            for app in space.apps():
                # do not account for 0 instance
                if app["entity"]["instances"] == 0:
                    continue

                # do not account for stopped and temporary conduit apps
                if (
                    app["entity"]["state"] == "STOPPED"
                    or "conduit" in app["entity"]["name"]
                ):
                    continue

                # do not account for docker images
                if app["entity"]["docker_image"]:
                    continue

                stack_info = json.loads(
                    client.get(
                        url=f'{os.environ["CF_DOMAIN"]}{app["entity"]["stack_url"]}'
                    ).text
                )
                cflinuxfs_name = stack_info["entity"]["name"]

                if cflinuxfs_name == "cflinuxfs3":
                    cflinux_list.append(
                        [
                            org["entity"]["name"],
                            space["entity"]["name"],
                            app["entity"]["name"],
                            cflinuxfs_name,
                        ]
                    )

    return cflinux_list


def _scan_postgres(client):
    postgres_list = []
    for org in client.v2.organizations:
        for space in org.spaces():
            for app in space.apps():
                for sb in app.service_bindings():
                    service = sb.service_instance()

                    if (
                        service["entity"]["type"] != "user_provided_service_instance"
                        and "autoscaler" not in service["entity"]["name"]
                    ):
                        try:
                            plan = service.service_plan()
                        except BaseException:
                            continue

                        if (
                            "Postgres Version 10" in plan["entity"]["description"]
                            or "Postgres Version 11" in plan["entity"]["description"]
                        ):
                            binding_count = service.service_bindings().total_results

                            bound_text = "UNBOUND" if not binding_count else ""
                            postgres_list.append(
                                [
                                    org["entity"]["name"],
                                    space["entity"]["name"],
                                    service["entity"]["name"],
                                    plan["entity"]["name"],
                                    bound_text,
                                ]
                            )

    return postgres_list


def _scan_redis(client):
    redis_list = []
    for org in client.v2.organizations:
        for space in org.spaces():
            for app in space.apps():
                for sb in app.service_bindings():
                    service = sb.service_instance()

                    if (
                        service["entity"]["type"] != "user_provided_service_instance"
                        and "autoscaler" not in service["entity"]["name"]
                    ):
                        try:
                            plan = service.service_plan()
                        except BaseException:
                            continue

                        if (
                            "Postgres" not in plan["entity"]["description"]
                            and "S3" not in plan["entity"]["description"]
                            and plan["entity"]["name"][-1] != "1"
                            and "5" not in plan["entity"]["name"]
                            and "6" not in plan["entity"]["name"]
                        ):
                            binding_count = service.service_bindings().total_results

                            bound_text = "UNBOUND" if not binding_count else ""

                            redis_list.append(
                                [
                                    org["entity"]["name"],
                                    space["entity"]["name"],
                                    service["entity"]["name"],
                                    plan["entity"]["name"],
                                    bound_text,
                                ]
                            )
    return redis_list


def write_csv(filename, data):
    with open(file=filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(data)


if __name__ == "__main__":
    proxy = dict(
        http=os.environ.get("HTTP_PROXY", ""), https=os.environ.get("HTTPS_PROXY", "")
    )

    if os.environ.get("CF_USERNAME"):
        client = CloudFoundryClient(target_endpoint=os.environ["CF_DOMAIN"])
        client.init_with_user_credentials(
            os.environ["CF_USERNAME"], os.environ["CF_PASSWORD"]
        )
    else:
        # Run using cf cli auth
        client = CloudFoundryClient.build_from_cf_config()

    is_weekday = dt.date.today().weekday() < 5

    if is_weekday:
        print("Performing scan ...")

        if SCAN_POSTGRES:
            postgres_list = _scan_postgres(client=client)
            postgres_list = [
                ["dit-services", "helpdesk", "pg-help-desk-service", "small-ha-11", ""]
            ]
            send_slack_message(header="Postgres instance report", data=postgres_list)

            if GENERATE_CSV:
                postgres_list.insert(
                    0, 0, ["organisation", "space", "service", "plan", "bound"]
                )
                write_csv(filename="postgres.csv", data=postgres_list)

        if SCAN_REDIS:
            redis_list = _scan_redis(client=client)
            send_slack_message(header="Redis instance report", data=redis_list)

            if GENERATE_CSV:
                redis_list.insert(
                    0, ["organisation", "space", "service", "plan", "bound"]
                )
                write_csv(filename="redis.csv", data=redis_list)

        if SCAN_CFLINUX:
            cflinux_list = _scan_cflinuxfs(client=client)

            send_slack_message(header="CFLinux report", data=cflinux_list)

            if GENERATE_CSV:
                cflinux_list.insert(0, ["organisation", "space", "app", "filesystem"])
                write_csv(filename="cflinuxfs3.csv", data=cflinux_list)

        print("Scan complete ...")
