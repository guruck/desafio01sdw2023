"""teste conexao e captura de informacoes sobre contas em SO UNIX"""

import sys
from typing import Dict
from datetime import date, timedelta
import select
import socket
from time import sleep

import paramiko as pmk
from paramiko import (
    AuthenticationException,
    BadAuthenticationType,
    BadHostKeyException,
    ChannelException,
    ConfigParseError,
    CouldNotCanonicalize,
    PasswordRequiredException,
    ProxyCommandFailure,
    SSHException,
)


class informsUnix:
    """_summary_ classe para controlar o trem bao"""

    POLL_INTERVALS = 0.5

    def __init__(self, enderecoip: str, username: str, porta: int = 22, pathkey: str = "") -> None:
        """_summary_

        Arguments:
            enderecoip -- _description_ endereco IP do equipamento a ser conectado
            username -- _description_ usuario credenciado utilizado para fechar a conexao com equipamento

        Keyword Arguments:
            porta -- _description_ (default: {22}) porta destino do servido a ser utilizada na conexao
            pathkey -- _description_ (default: {""}) local do certificado para conexao se utilizado
        """
        self._ip: str = enderecoip
        self._porta: int = porta
        self._user: str = username
        self._pathkey: str = pathkey
        self._passwd: str = "testando" if self._user == "testando" else ""
        self._conn: pmk.SSHClient = pmk.SSHClient()
        self._closed: bool = True

    def _setConnection(self):
        """cria uma conexao SSH com determinado servidor para uso"""
        try:
            client = self._conn
            client.set_missing_host_key_policy(pmk.AutoAddPolicy())
            client.connect(hostname=self._ip, port=self._porta, username=self._user, password=self._passwd, timeout=2)
            self._conn = client
            self._closed = False
        except (
            SSHException,
            AuthenticationException,
            PasswordRequiredException,
            BadAuthenticationType,
            ChannelException,
            BadHostKeyException,
            ProxyCommandFailure,
            CouldNotCanonicalize,
            ConfigParseError,
            TimeoutError,
            ConnectionError,
        ) as sshexc:
            class_err = self.__getErrorName(str(sshexc.__class__))
            sshexc.args(
                {
                    f"{class_err} on {self._ip}: {sshexc}",
                }
            )
            raise sshexc
        except BaseException as sshexc:
            class_err = self.__getErrorName(str(sshexc.__class__))
            raise NotImplementedError(f"GeneralSSHError [{class_err}] on {self._ip}: {sshexc}") from sshexc

    def start(self):
        """executa um determinado comando"""
        if self._closed:
            self._setConnection()
            # is_active can be a false positive, so further test
        transport = self._conn.get_transport()
        if transport.is_active():
            try:
                transport.send_ignore()
            except Exception as _e:
                print("Falhou no teste da conexão já era... pode parar")
                raise _e
        else:
            print("Falhou no teste da conexão já era... pode parar")
            raise SSHException("Falhou no teste da conexão já era... pode parar")

    def execute(self, command: str, timeout=5, get_pty: bool = False):
        """executa um determinado comando"""
        try:
            """ ERROR=> a terminal is required to read the password; either use the -S option to read
                        from standard input or configure an askpass helper
                SE o usuario tem sudo, mas nao tem permissao de executar o comando sem senha
                ERROR=> sudo: sorry, you must have a tty to run sudo
                SE a configuracao 'Defaults  requiretty' estiver ativada em sudores , get_pty=TRUE
                ERROR=> TimeoutError on 127.0.0.1:
                SE o usuario tem sudo, mas nao tem permissao de executar o comando sem senha com o get_pty=TRUE

                Para execucao sem problemas com sudoers 'Defaults  requiretty', necessario que o get_pty=TRUE
                e tambem que o usuario tenha configurado para nao utilizar senha.
                Exemplo: testando    ALL=(ALL:ALL)  NOPASSWD:/usr/bin/passwd
            """
            _stdin, _stdout, _stderr = self._conn.exec_command(command, timeout=timeout, get_pty=get_pty)
            err = _stderr.read().decode()
            if err != "":
                message = err.split("\n")
                raise SSHException(message[0])

            return _stdout.read().decode()
        except (SSHException, ChannelException, TimeoutError) as sshexc:
            class_err = self.__getErrorName(str(sshexc.__class__))
            raise SSHException(f"{class_err} on {self._ip}: {sshexc}") from sshexc
        except BaseException as sshexc:
            class_err = self.__getErrorName(str(sshexc.__class__))
            raise NotImplementedError(f"CommandSSHError [{class_err}] on {self._ip}: {sshexc}") from sshexc

    def __chanelcommand(self, command):
        transport = self._conn.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        # We're not handling stdout & stderr separately
        channel.set_combine_stderr(1)
        channel.exec_command(command)
        # Command was sent, no longer need stdin
        channel.shutdown_write()
        # iterate over each yield as it is given
        for response in self.__responseGen(channel):
            sys.stdout.write(response)

    def __execute_command(
        self, command, out_streams=[sys.stdout], err_streams=[sys.stderr], poll_intervals=POLL_INTERVALS
    ):
        # Pre-pend required environment here
        command = "TERM=xterm " + command
        stdin, stdout, stderr = self._conn.exec_command(command)
        stdin.write(self._passwd)
        stdin.flush()
        channel = stdout.channel
        stdin.close()
        channel.shutdown_write()
        while not channel.closed or channel.recv_ready() or channel.recv_stderr_ready():
            got_data = False
            output_channels = select.select([channel], [], [], poll_intervals)[0]

            if output_channels:
                channel = output_channels[0]
                if channel.recv_ready():
                    for stream in out_streams:
                        stream.write(channel.recv(len(channel.in_buffer)))
                        stream.flush()
                    got_data = True

                if channel.recv_stderr_ready():
                    for stream in err_streams:
                        stream.write(channel.recv_stderr(len(channel.in_stderr_buffer)))
                        stream.flush()
                    got_data = True

            if (
                not got_data
                and channel.exit_status_ready()
                and not channel.recv_ready()
                and not channel.recv_stderr_ready()
            ):
                channel.shutdown_read()
                channel.close()
                break

        return channel.recv_exit_status()

    def endConection(self):
        """executa um determinado comando"""
        if self._closed is False:
            self._conn.close()
            self._closed = True

    def __getErrorName(self, typeClassName: str) -> str:
        """captura o nome do erro a partir da string do tipo da classe"""
        class_err = typeClassName[8:-2]
        err_lst = class_err.split(".")
        if len(err_lst) > 1:
            class_err = err_lst[len(err_lst) - 1]
        return class_err

    def __responseGen(self, channel):
        # Small outputs (i.e. 'whoami') can end up running too quickly
        # so we yield channel.recv in both scenarios
        # while True:
        #     if channel.recv_ready():
        #         yield channel.recv(4096).decode("utf-8")

        #     if channel.exit_status_ready():
        #         yield channel.recv(4096).decode("utf-8")
        #         break
        while True:
            sleep(0.1)
            backMsg = ""
            try:
                backMsg = channel.recv(65536).decode("utf-8")
            except socket.timeout as e:
                raise e
            prints = "backMsg:%s, length:%d, channel recv status:%d " % (backMsg, len(backMsg), channel.recv_ready())
            print(prints)
            if len(backMsg) == 0 and channel.recv_ready() is False:
                break


def getData(dias: str):
    if int(dias):
        base_date = date(1970, 1, 1)
        td = base_date + timedelta(int(dias))
        return f"{td.day:02d}/{td.month:02d}/{td.year}"


def getUsersDetailsUnix() -> None:
    final_users = []
    list_users: Dict[str, list[str]] = {}
    group_prim: Dict[str, str] = {}
    expirations_users: list[list[str]] = []

    client = informsUnix(enderecoip="127.0.0.1", username="testando")
    try:
        client.start()
    except Exception as e:
        print("Falhou na conexão já era... pode parar")
        raise e

    try:
        command = "cat /etc/passwd | grep -v bin/nologin | grep -v bin/false | cut -d: -f 1,4"
        lines = client.execute(command)

        output = lines.split("\n")
        if isinstance(output, list) and len(output) > 1:  # geralmente sobra 1 \n vazio
            for line in output:
                if line != "":
                    str_aux = str(line).split(":")
                    list_users.setdefault(str_aux[0], [str_aux[1]])
        else:
            print("There was no output for this command")

    except Exception as e:
        print("Conectou mas nada de usuario, já era... pode parar")
        raise e

    try:
        command = "cat /etc/group | cut -d: -f 1,3,4"
        lines = client.execute(command)

        output = lines.split("\n")
        if isinstance(output, list) and len(output) > 1:  # geralmente sobra 1 \n vazio
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
    except Exception as e:
        print("Existe Usuarios, mas não retornou os Grupos, continua mas faz o LOG disso e notifica")
        print(e)

    try:
        command = "sudo -l -U testando"  # noqa: E501, pylint: disable=fixme, line-too-long
        command = "for user in $(cat /etc/passwd | grep -v bin/nologin | grep -v bin/false | cut -d: -f 1); do sudo passwd -S $user | cut -d' ' -f 1,2,3,5; done"  # noqa: E501, pylint: disable=fixme, line-too-long
        lines = client.execute(command, get_pty=True)

        output = lines.split("\n")
        if isinstance(output, list) and len(output) > 1:  # geralmente sobra 1 \n vazio
            for line in output:
                if line != "":
                    str_aux = line.replace("\r", "")
                    str_aux = str(str_aux).split(" ")
                    str_aux[1] = "Disable" if str_aux[1] in ('L', 'LK') else "Enable"
                    str_aux[3] = "never" if str_aux[3] in ('-1', '99999') else str_aux[3]
                    expirations_users.append(str_aux)
        else:
            for user in list_users:
                str_aux = [user, "Enable", "", ""]
                expirations_users.append(str_aux)
            print("There was no output for this command")

        for a, b, c, d in expirations_users:
            final_users.append([a, b, c, d, list_users.get(a)])

    except Exception as e:
        print("Existe Usuarios, mas não retornou o Detalhe, continua mas faz o LOG disso e notifica")
        print(e)

    print(f"\nfinal_users[{len(final_users)}]: ", final_users)


if __name__ == "__main__":
    getUsersDetailsUnix()
