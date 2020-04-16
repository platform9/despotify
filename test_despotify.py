import json
import os
import random
import unittest
from unittest import mock

import timeout_decorator
import despotify.despotify as despotify


class MockResponse:
    def __init__(self,
                 text='',
                 status_code=200):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)


def mocked_yes_termination_notice(*args, **kwargs):
    return MockResponse(status_code=200)


def mocked_no_termination_notice(*args, **kwargs):
    return MockResponse(status_code=404)


def mocked_instance_id_ok(*args, **kwargs):
    return MockResponse(text="inst-0001", status_code=200)


def mocked_instance_identity_ok(*args, **kwargs):
    mock_resp_json = {"accountId" : "110072563648",
                      "architecture" : "x86_64",
                      "availabilityZone" : "us-west-2b",
                      "billingProducts" : None,
                      "devpayProductCodes" : None,
                      "marketplaceProductCodes" : None,
                      "imageId" : "ami-c62eaabe",
                      "instanceId" : "i-0fdf4238481104526",
                      "instanceType" : "t2.medium",
                      "kernelId" : None,
                      "pendingTime" : "2019-12-16T20:20:38Z",
                      "privateIp" : "10.0.2.97",
                      "ramdiskId" : None,
                      "region" : "us-west-2",
                      "version" : "2017-09-30"}
    mock_resp_str = json.dumps(mock_resp_json)
    return MockResponse(text=mock_resp_str, status_code=200)


def mocked_instance_type_ok(*args, **kwargs):
    return MockResponse(text="t2.medium", status_code=200)

def mocked_monitor_termination_notice(*args, **kwargs):
    # Setting probability of a termination notice to 20%
    prob = random.randint(0, 10)
    if prob < 2:
        return mocked_yes_termination_notice(args, kwargs)
    return mocked_no_termination_notice(args, kwargs)

def mocked_asg_name(*args, **kwargs):
    return b'spot-worker-f21f78ae-4766-44e0-90c0-282ce8a2ff80\n'

def mocked_run_cmd(*args, **kwargs):
    return ""


class TestDespotify(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        despotify.setup_logging()

    @mock.patch('requests.get', side_effect=mocked_no_termination_notice)
    def test_no_termination_notice(self, _):
        notice_received = despotify.termination_notice_received()
        self.assertFalse(notice_received)

    @mock.patch('requests.get', side_effect=mocked_yes_termination_notice)
    # The unused '_' variable is a pointer to the mocked method
    def test_termination_notice(self, _):
        notice_received = despotify.termination_notice_received()
        self.assertTrue(notice_received)

    def test_get_node_name_set(self):
        os.environ['POD_NODE_NAME'] = 'node1'
        name = despotify.node_name()
        self.assertEqual(name, "node1")
        os.environ.pop('POD_NODE_NAME')

    def test_get_node_name_unset(self):
        name = despotify.node_name()
        self.assertEqual(name, "")

    def test_get_pod_name_set(self):
        os.environ['POD_NAME'] = 'despotify-pod'
        name = despotify.pod_name()
        self.assertEqual(name, "despotify-pod")
        os.environ.pop('POD_NAME')

    def test_get_pod_name_unset(self):
        name = despotify.pod_name()
        self.assertEqual(name, "")

    @mock.patch('requests.get', side_effect=mocked_instance_identity_ok)
    def test_get_region_name_ok(self, _):
        name = despotify.aws_region()
        self.assertEqual(name, "us-west-2")

    @mock.patch('requests.get', side_effect=mocked_instance_id_ok)
    def test_get_instance_id_ok(self, _):
        instance_id = despotify.instance_id()
        self.assertEqual(instance_id, 'inst-0001')

    @mock.patch('requests.get', side_effect=mocked_instance_type_ok)
    def test_get_instance_type_ok(self, _):
        instance_type = despotify.instance_type()
        self.assertEqual(instance_type, 't2.medium')

    @mock.patch('requests.get', side_effect=mocked_monitor_termination_notice)
    @mock.patch('despotify.despotify.asg_name', side_effect=mocked_asg_name)
    @mock.patch('despotify.despotify._run_cmd', side_effect=mocked_run_cmd)
    @timeout_decorator.timeout(60)
    def test_monitor_termination_notice(self, _1, _2, _3):
        despotify.monitor_termination_notice()

    def test_global_var_config(self):
        despotify.configure_global_vars()

if __name__ == '__main__':
    unittest.main()
