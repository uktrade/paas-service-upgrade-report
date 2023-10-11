# pass audit script

to audit cloud foundry pass platform for outdated versions of

- postgres
- redis
- cflinuxfs

### Devlopment

uses devcontainer extension of vscode for quick and easy setup, you will need to setup `.env` file with-in `.devcontainer` directory, for setup to work as expected

example `.env` file

```bash
CF_USERNAME=Your cloud foundry user
CF_PASSWORD=Cloud foundry user password
CF_DOMAIN=https://your.cf.api.endpoint
SLACK_CHANNEL=slack channel id
SLACK_URL=webhook URL
SCAN_POSTGRES=False
SCAN_REDIS=False
SCAN_CFLINUX=True
GENERATE_CSV=False
GIT_USER_NAME=Firstname Lastname
GIT_EMAIL=your@git.email
GIT_COMMIT_EDITOR=code -w
```
