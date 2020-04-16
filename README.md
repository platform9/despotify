despotify: AWS Spot Instance Termination Notice Handler for Kubernetes Nodes
---

Despotify is a service designed to run on a PMK-on-AWS cluster to monitor and
manage nodes that are spot instances.

Despotify is meant to be deployed as a DaemonSet, so that it is able to run on
all nodes. Once deployed, each node has despotify periodically query the
instance metadata for a termination notice. AWS typically issues a termination
notice two minutes ahead of time. Once despotify detects a termination notice,
it performs the following actions:

* *Detach the node from the ASG*. This will result in AWS spawning a new node sooner, before this node is terminated.
* *Safely drain the node of all kubernetes objects running on it*. This will get
kubernetes to reschedule these objects onto other available nodes and prevent
kubernetes from scheduling further resources on this node.

Despotify itself is killed when the node is terminated.

# Configuration
All configuration options go into `despotify.ini`. The following options work:
```
[DEFAULT]
# Log level - valid options are INFO, DEBUG, WARNING.
level = INFO
# Poll Interval - Time in seconds to query for a termination notice. Default: 5
# poll_interval =
# Grace Period - Time in seconds that kuberenetes has to clean the node up. Default: 120
# grace_period =

# Notice URL - The metadata API to fetch termination notice. Default: http://169.254.169.254/latest/meta-data/spot/termination-time
# notice_url =
# Instance ID URL - The metadata API to fetch the instance ID. Default: http://169.254.169.254/latest/meta-data/instance-id
# inst_id_url =
# Instance Type URL - The metadata API to fetch instance type. Default: http://169.254.169.254/latest/meta-data/instance-type
# inst_type_url =
# Instance identity URL - The metadata API to fetch the instance identity documentation. Default: http://169.254.169.254/latest/meta-data/instance-identity/document
# inst_identity_url =
```
# Usage
To run the service by hand:
```
$ python3 despotify.py
```

Via Docker:
```
$ docker run platform9/despotify:1.0.0
```

# Known Issues