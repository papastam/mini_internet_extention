# Slack integration

During the project at ETH Zürich, we also operate a Slack workspace dedicated to our lecture and the mini-Internet project.
We use a couple of Slack integrations (using Slack Incooming [webhooks](https://api.slack.com/messaging/webhooks) that improve students' experience. 
We describe them in this section.

:point_right: For each script, you will have to update the webhook URL so that it corresponds to your Slack workspace.

## Connectivity Robot

Every day the `utils/slack/matrix_notif.py` script writes the current connectivity score to a given Slack channel (e.g., the one dedicated to the mini-Internet project). The connectivity score is computed from the raw data used to generate the matrix on the website. 
The raw data is accessible in json at this url: `https://your-server-domain/matrix?raw`.

## SSH processes in proxy containers

Every hour the `utils/slack/ssh_proxy_notif.sh` script checks the number of processes running in each SSH proxy container.
If this number exceeds a threshold (e.g., 75), a notification is sent to a Slack channel dedicated to the TA team.
One TA can thus kill some of the processes running in the SSH proxy container to prevent reaching the maximum number of processes (100).
In case this threshold is reached, accessing the SSH proxy container might no longer be possible (even using the docker commands) and you need
to [restart the container](restart_container).

:exclamation: We are currently working on ways to automate this process.
