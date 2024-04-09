"""teste conexao"""

from typing import Dict
import paramiko as pmk
from datetime import date, timedelta


def getData(dias: str):
    if int(dias):
        base_date = date(1970, 1, 1)
        td = base_date + timedelta(int(dias))
        return f"{td.day:02d}/{td.month:02d}/{td.year}"


def getUsersDetailsUnix() -> None:
    host = "172.20.116.114"
    username = "testando"
    password = "testando"
    final_users = []
    list_users: Dict[str, list[str]] = {}
    group_prim: Dict[str, str] = {}
    status_users: Dict[str, str] = {}
    expirations_users: list[list[str]] = []

    try:
        client = pmk.client.SSHClient()
        client.set_missing_host_key_policy(pmk.AutoAddPolicy())
        client.connect(host, username=username, password=password, port=22)
        _stdin, _stdout, _stderr = client.exec_command("cat /etc/passwd | cut -d: -f 1,4")
        lines = _stdout.read().decode()
        output = lines.split("\n")
        if list_users != "":
            output.remove("")
            for line in output:
                if line != "":
                    str_aux = str(line).split(":")
                    list_users.setdefault(str_aux[0], [str_aux[1]])
        else:
            print("There was no output for this command")

        _stdin, _stdout, _stderr = client.exec_command("cat /etc/group | cut -d: -f 1,3,4")
        lines = _stdout.read().decode()

        output = lines.split("\n")
        if output != "":
            for line in output:
                if line != "":
                    str_aux = str(line).split(":")
                    grupo = str_aux[0]
                    gpid = str_aux[1]
                    users = str_aux[2].split(",")
                    group_prim.update({gpid: grupo})
                    for user in users:
                        if user != "":
                            grps = list_users.get(user)
                            if grps is not None:
                                if grupo not in grps:
                                    grps.append(grupo)
                                    list_users.update({user: grps})
        else:
            print("There was no output for this command")

        for user in list_users:
            grp = list_users.get(user)
            if grp is not None:
                aux = group_prim.get(grp[0])
                if aux in grp:
                    grp.pop(0)
                elif aux is not None:
                    grp[0] = aux
                list_users.update({user: grp})

        _stdin, _stdout, _stderr = client.exec_command('sudo bash -c "passwd -S --all"')
        lines = _stdout.read().decode()
        output = lines.split("\n")
        if output != "":
            for line in output:
                if line != "":
                    str_aux = str(line).split(" ")
                    status_users.update({str_aux[0]: str_aux[1]})
        else:
            print("There was no output for this command")

        _stdin, _stdout, _stderr = client.exec_command('sudo bash -c "cat /etc/shadow | cut -d: -f 1,3,8"')
        lines = _stdout.read().decode()
        output = lines.split("\n")
        if output != "":
            for line in output:
                if line != "":
                    str_aux = str(line).split(":")
                    str_aux[1] = getData(str_aux[1])
                    str_aux[2] = "never" if str_aux[2] == "" else str_aux[2]
                    expirations_users.append(str_aux)
        else:
            print("There was no output for this command")

        for a, b, c in expirations_users:
            final_users.append([a, b, c, status_users.get(a), list_users.get(a)])

    except Exception as e:
        print(e)
    finally:
        client.close()

    print(f"\nfinal_users[{len(final_users)}]: ", final_users)


if __name__ == "__main__":
    getUsersDetailsUnix()
