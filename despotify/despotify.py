#!/usr/bin/env python
# Copyright (c) 2019 Platform9 Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# according to http://eventlet.net/doc/patching.html, eventlet will
# patch python standard libs, but thread in eventlet
# causes deadlock when use together with python's standard thread
# methods. to avoid this, exclude the thread module from start
# point of application to avoid thread deadlock problem.


import subprocess
import sys
import threading
import time
# import json
import configparser
import logging
import os
import requests


CONFIG_FILE = 'despotify.ini'
NOTICE_URL = "http://169.254.169.254/latest/meta-data/spot/termination-time"
PUBLIC_IP_URL = "http://169.254.169.254/latest/meta-data/public-ipv4"
INST_ID_URL = "http://169.254.169.254/latest/meta-data/instance-id"
INST_IDENTITY_URL = "http://169.254.169.254/latest/dynamic/instance-identity/document"
SLACK_CHANNEL = "#leb-spot-test"
SLACK_USERNAME = "terminator"
POLL_INTERVAL = 5
# AWS gives us a 2 minute notice - so that's how long we have to clean the node up
GRACE_PERIOD = 120
LOG_LEVEL = 'INFO'
g_inst_id = '(unknown instance id)'
g_inst_identity_url = ''
g_notice_url = ''
g_slack_url = ''
g_slack_channel = ''
g_slack_username = ''
g_region = '(unknown region)'
g_private_ip = '(unknown private ip)'
g_public_ip = '(unknown public ip)'
g_detach = False


def setup_logging():
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(LOG_LEVEL)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] : %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)


def _run_cmd(command):
    cmd_list = command.split(" ")
    try:
        out = subprocess.run(cmd_list, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, check=True)
        cmd_output = out.stdout.decode('UTF-8').strip()
    except subprocess.CalledProcessError as proc_e:
        logging.error("Command failed to run:(%s) %s", proc_e.returncode, proc_e.stderr)
        raise proc_e

    return cmd_output


def termination_notice_received(notice_url=NOTICE_URL):
    try:
        resp = requests.get(notice_url, timeout=POLL_INTERVAL)
    except requests.exceptions.ConnectionError:
        logging.exception("termination notice request failed")
        return False
    except requests.exceptions.ReadTimeout:
        logging.warning("termination notice request timed out after %s seconds",
                        POLL_INTERVAL)
        return False

    if resp.status_code != 200:
        logging.warning("termination notice status=%d reason=%s",
                        resp.status_code, resp.reason)
        return False
    try:
        j = resp.json()
    except ValueError:
        # not json, return now
        logging.info('termination notice returned: %s', resp.text)
        return True
    logging.info('termination notice returned json: %s', j)
    try:
        itt = j['instances_to_terminate']
        if type(itt) is not list:
            logging.warning('instances_to_terminate is not a list, aborting.')
            return False
        for key in (g_inst_id, g_private_ip, g_public_ip):
            if key in itt:
                logging.info('%s found in instances_to_terminate' % key)
                return True
    except:
        logging.exception('failed to decode instances_to_terminate from json')
        return False
    logging.warning('%s, %s, and %s not found in instances_to_terminate' % (
        g_inst_id, g_private_ip, g_public_ip))
    return False


def node_name():
    name = os.environ.get('POD_NODE_NAME', '')
    logging.debug("Node name: %s", name)
    return name


def pod_name():
    name = os.environ.get('POD_NAME', '')
    logging.debug("Pod name: %s", name)
    return name


def get_aws_region_and_private_ip():
    global g_region
    global g_private_ip
    try:
        resp = requests.get(g_inst_identity_url)
    except:
        logging.exception('failed to get region and private ip')
        return

    if resp.status_code != 200:
        logging.warning("Instance identity request failed with status: %s",
                        resp.status_code)
        return

    inst_identity = resp.json()
    g_region = inst_identity['region']
    g_private_ip = inst_identity['privateIp']
    logging.debug("AWS region: %s", g_region)
    logging.debug("private ip: %s", g_private_ip)


def get_public_ip():
    global g_public_ip

    try:
        resp = requests.get(PUBLIC_IP_URL)
    except:
        logging.exception('failed to get public ip')
        return

    if resp.status_code != 200:
        logging.warning("Public ip request failed with status: %s",
                        resp.status_code)
        return

    g_public_ip = resp.text
    logging.debug("public ip: %s", g_public_ip)


def get_instance_id(inst_id_url):
    global g_inst_id

    try:
        resp = requests.get(inst_id_url)
    except:
        logging.exception('failed to get instance id')
        return
    if resp.status_code != 200:
        logging.warning("Instance ID request failed with status: %s",
                        resp.status_code)
        return

    g_inst_id = resp.text
    logging.debug("Instance ID: %s", g_inst_id)


def asg_name():
    cmd = "aws --output text " +\
           "--query AutoScalingInstances[0].AutoScalingGroupName " +\
           "--region %s " % g_region +\
           "autoscaling describe-auto-scaling-instances " +\
           "--instance-ids %s" % g_inst_id

    asg = _run_cmd(cmd)
    logging.debug("ASG Name: %s", asg)
    return asg


def detach_from_asg():
    asg = asg_name()
    detach_cmd = "aws --region %s " % g_region +\
                 "autoscaling detach-instances " +\
                 "--instance-ids %s " % g_inst_id +\
                 "--auto-scaling-group-name %s " %(asg) +\
                 "--no-should-decrement-desired-capacity"

    _ = _run_cmd(detach_cmd)
    logging.info("Node detached from ASG.")


def drain_node():
    node = node_name()
    drain_cmd = "kubectl drain %s " % node +\
                "--force --ignore-daemonsets " +\
                "--delete-local-data --grace-period=%s" % GRACE_PERIOD
    logging.info("Runnning drain command: %s", drain_cmd)
    _ = _run_cmd(drain_cmd)
    logging.info("Node drained successfully.")


def post_to_slack(channel, username, txt, icon_emoji=':terminator:'):
    if not g_slack_url:
        return
    pl = '{"channel": "%s","username": "%s","icon_emoji":"%s","text": "%s"}' % \
         (channel, username, icon_emoji, txt)
    r = requests.post(g_slack_url, data={'payload': pl})
    if r.status_code != 200:
        logging.warn('failed to post to slack: status=%d reason=%s',
                     r.status_code, r.reason)


def monitor_termination_notice():
    msg = 'instance %s / %s / %s monitored for termination...' % (
        g_inst_id, g_private_ip, g_public_ip)
    logging.info("Waiting for termination notice from AWS. Querying every %ss.",
                 POLL_INTERVAL)
    post_to_slack(g_slack_channel, g_slack_username, msg)
    logging.info(msg)
    while True:
        if termination_notice_received(notice_url=g_notice_url):
            logging.info("Termination notice received.")
            logging.info("Detaching the node from the ASG and cleaning it up.")
            break
        time.sleep(POLL_INTERVAL)

    post_to_slack(g_slack_channel, g_slack_username,
                  'starting termination sequence for %s / %s / %s' %
                  (g_inst_id, g_private_ip, g_public_ip))
    if g_detach:
        logging.info('detaching from asg is enabled ...')
        # Running detach_from_asg and drain_node concurrently to save time.
        detach_thread = threading.Thread(target=detach_from_asg)
        detach_thread.start()
    else:
        logging.info('NOT detaching from asg')
    drain_node()


def configure_global_vars():
    global g_notice_url
    global g_slack_url
    global POLL_INTERVAL
    global GRACE_PERIOD
    global LOG_LEVEL
    global g_inst_identity_url
    global g_slack_channel
    global g_slack_username
    global g_detach

    conf = configparser.ConfigParser()
    conf.read(CONFIG_FILE)

    g_notice_url = conf.get('DEFAULT', 'notice_url', fallback=NOTICE_URL)
    g_slack_url = conf.get('DEFAULT', 'slack_url', fallback=None)
    g_slack_channel = conf.get('DEFAULT', 'slack_channel',
                               fallback=SLACK_CHANNEL)
    g_slack_username = conf.get('DEFAULT', 'slack_username',
                                fallback=SLACK_USERNAME)
    inst_id_url = conf.get('DEFAULT', 'inst_id_url', fallback=INST_ID_URL)
    g_inst_identity_url = conf.get('DEFAULT', 'inst_identity_url', fallback=INST_IDENTITY_URL)
    POLL_INTERVAL = int(conf.get('DEFAULT', 'poll_interval', fallback=POLL_INTERVAL))
    GRACE_PERIOD = int(conf.get('DEFAULT', 'grace_period', fallback=GRACE_PERIOD))
    LOG_LEVEL = conf.get('DEFAULT', 'level', fallback=LOG_LEVEL)
    g_detach = conf.get('DEFAULT', 'detach_from_asg', fallback='false') == 'true'
    get_instance_id(inst_id_url=inst_id_url)
    get_aws_region_and_private_ip()
    get_public_ip()


if __name__ == '__main__':
    configure_global_vars()
    setup_logging()
    monitor_termination_notice()
    # Sleep to ensure that this script doesn't exit and is restarted. We expect
    # the instance to be terminated by the end of this sleep.
    time.sleep(200)
