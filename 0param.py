"""teste conexao"""

from typing import Dict
from datetime import date, timedelta

import paramiko as pmk
from paramiko import (
    AuthenticationException,
    BadAuthenticationType,
    BadHostKeyException,
    ChannelException,
    ConfigParseError,
    CouldNotCanonicalize,
    IncompatiblePeer,
    PasswordRequiredException,
    ProxyCommandFailure,
    SSHException,
)


class informsUnix:
    """classe para controlar o trem bao"""

    def __init__(self, enderecoip, username, porta=22, pathkey="") -> None:
        self._ip = enderecoip
        self._porta = porta
        self._user = username
        self._pathkey = pathkey
        self._conn = self._setConnection()

    def _setConnection(self) -> pmk.SSHClient:
        """cria uma conexao SSH com determinado servidor para uso"""
        password = "testando" if self._user == "testando" else ""
        try:
            client = pmk.SSHClient()
            client.set_missing_host_key_policy(pmk.AutoAddPolicy())
            client.connect(hostname=self._ip, port=self._porta, username=self._user, password=password)
            return client
        except (
            SSHException,
            AuthenticationException,
            PasswordRequiredException,
            BadAuthenticationType,
            ChannelException,
            BadHostKeyException,
            IncompatiblePeer,
            ProxyCommandFailure,
            CouldNotCanonicalize,
            ConfigParseError,
            TimeoutError,
            ConnectionError,
        ) as sshexc:
            class_err = self.__getErrorName(str(sshexc.__class__))
            raise SSHException(f"{class_err} on {self._ip}: {sshexc}") from sshexc
        except BaseException as sshexc:
            class_err = self.__getErrorName(str(sshexc.__class__))
            raise NotImplementedError(f"GeneralSSHError [{class_err}] on {self._ip}: {sshexc}") from sshexc

    def execute(self, command: str):
        """executa um determinado comando"""
        try:
            _stdin, _stdout, _stderr = self._conn.exec_command(command)
            lines = _stdout.read().decode()
            return lines
        except (SSHException, ChannelException, TimeoutError) as sshexc:
            class_err = self.__getErrorName(str(sshexc.__class__))
            raise SSHException(f"{class_err} on {self._ip}: {sshexc}") from sshexc
        except BaseException as sshexc:
            class_err = self.__getErrorName(str(sshexc.__class__))
            raise NotImplementedError(f"CommandSSHError [{class_err}] on {self._ip}: {sshexc}") from sshexc

    def endConection(self):
        """executa um determinado comando"""
        if self._conn:
            self._conn.close()

    def __getErrorName(self, typeClassName: str) -> str:
        """captura o nome do erro a partir da string do tipo da classe"""
        class_err = typeClassName[8:-2]
        err_lst = class_err.split(".")
        if len(err_lst) > 1:
            class_err = err_lst[len(err_lst) - 1]
        return class_err


def getData(dias: str):
    if int(dias):
        base_date = date(1970, 1, 1)
        td = base_date + timedelta(int(dias))
        return f"{td.day:02d}/{td.month:02d}/{td.year}"


def getUsersDetailsUnix() -> None:
    final_users = []
    list_users: Dict[str, list[str]] = {}
    group_prim: Dict[str, str] = {}
    status_users: Dict[str, str] = {}
    expirations_users: list[list[str]] = []

    try:
        client = informsUnix(enderecoip="172.20.116.114", username="testando")
        lines = client.execute("cat /etc/passwd | cut -d: -f 1,4")

        output = lines.split("\n")
        if list_users != "":
            output.remove("")
            for line in output:
                if line != "":
                    str_aux = str(line).split(":")
                    list_users.setdefault(str_aux[0], [str_aux[1]])
        else:
            print("There was no output for this command")

        lines = client.execute("cat /etc/group | cut -d: -f 1,3,4")

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

        lines = client.execute('sudo bash -c "passwd -S --all"')

        output = lines.split("\n")
        if output != "":
            for line in output:
                if line != "":
                    str_aux = str(line).split(" ")
                    status_users.update({str_aux[0]: str_aux[1]})
        else:
            print("There was no output for this command")

        lines = client.execute('sudo bash -c "cat /etc/shadow | cut -d: -f 1,3,8"')

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

    print(f"\nfinal_users[{len(final_users)}]: ", final_users)


if __name__ == "__main__":
    getUsersDetailsUnix()
