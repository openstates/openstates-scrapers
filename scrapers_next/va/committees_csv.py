from paramiko.client import SSHClient, AutoAddPolicy
import paramiko
import time
from spatula import CsvListPage


class ChamberList(CsvListPage):
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy)
    connected = False
    attempts = 0
    while not connected:
        try:
            client.connect(
                "sftp.dlas.virginia.gov",
                username="rjohnson",
                password="E8Tmg%9Dn!e6dp",
                compress=True,
            )
        except paramiko.ssh_exception.AuthenticationException:
            attempts += 1
            # hacky backoff!
            time.sleep(attempts * 30)
        else:
            connected = True
        # importantly, we shouldn't try forever
        if attempts > 3:
            break
    if not connected:
        raise paramiko.ssh_exception.AuthenticationException
    sftp = client.open_sftp()
    sftp.chdir("/CSV221/csv231")

    source = sftp.open("Committees.csv")  # .read().decode(errors="ignore")

    def process_item(self, row):
        print("here")
