"""ETL que recebe de entrada um arquivo CSV com equipamentos de diversos fabricantes
com esses cadastrados de forma qualquer necessitando normaliza-los para encaminhar
para um sistema onde serao registrados, podendo ter a saida normalizada em formato
CSV ou JSON para carrega-los

Na proposta deve existir um arquivo DE-PARA para que os campos com ajustes a serem
realizados possam ter seus valores de antes e depois para transformar os dados

Existe na implementacao filtros que podem ser definidos a partir de regras como exemplo
equipamentos apenas instalados, ou equipamentos apenas de determinados fabricantes
"""

import re
import pandas as pd
import json
import time
import calendar


def normalize(campo: str, de_para: pd.DataFrame, default: str = "") -> str:
    """normalizacao generica para qualquer campo de um Dataframe
    a partir de um arquivo de controle de alteracoes 'de-para'
    """
    for _, value in de_para.iterrows():
        campo = str(campo).lower()
        if value.tipo == "association":
            if value.antes in campo:
                return value.depois
        elif value.tipo == "regexp":
            if re.search(value.antes, campo):
                return value.depois
    return campo if default == "" else default


# EXTRACAO DOS DADOS PARA TRANSFORMACAO
frame = pd.read_csv("desafiosdw23/equipamentos.csv", delimiter=";", encoding="UTF-8")
df_dados = pd.read_csv("desafiosdw23/de_para.csv", delimiter=";")

print(f"passo1 Extract Equipamentos:\n{frame}\n")
print(f"passo1 Extract DE-PARA:\n{df_dados}\n")

# TRANSFORMACAO DOS DADOS
# ## NORMALIZACAO
df_fabricante = df_dados.query("campo == 'FABRICANTE'")[["antes", "depois", "tipo"]]
df_modelo = df_dados.query("campo == 'MODELO'")[["antes", "depois", "tipo"]]

frame["FABRICANTE"] = frame["FABRICANTE"].apply(normalize, de_para=df_fabricante)
frame["MODELO"] = frame["MODELO"].apply(normalize, de_para=df_modelo, default="MD5")

# ## FILTROS
frame = frame.query(
    "STATUS == 'INSTALADO' & "
    "STATUS_OPERACIONAL == 'OPERACIONAL' & "
    "ARQUITETURA == 'TELECOM' & "
    "ENDERECO_IP != '' "
)

vendor_list = ["Cisco", "Juniper", "F5"]
vendor_query = " | ".join(f"FABRICANTE == '{vendor}'" for vendor in vendor_list)
frame = frame.query(vendor_query).reset_index(drop=True)  # drop=True
current_GMT = time.gmtime()
current_timestamp = calendar.timegm(current_GMT)
frame["ID"] = frame.index + current_timestamp
print(f"passo2 dados TRANSFORMADOS:\n{frame}\n")

# nesse ponto os dados em dataframe sao transformados na saida em JSON
json_list = json.loads(json.dumps(list(frame.T.to_dict().values())))
str_format = "".join(f"{item}," for item in json_list)
str_format = str_format[:-1].replace("'", '"')
str_format = '{"EQUIPAMENTOS": [' + str_format + "]}\n"
print(f"passo2 dados TRANSFORMADOS para JSON:\n{str_format}\n")

print("passo3 EXPORTANDO PARA ARQUIVO JSON: desafiosdw23/output.json")
with open("desafiosdw23/output.json", "w") as f:
    f.write(str_format)

# nesse ponto foi alterado o layout dos campos para facilitar a visualizacao do arquivo
print("passo3 EXPORTANDO PARA ARQUIVO CSV: desafiosdw23/equipamentos_transformados.csv")
frame[["ID", "STATUS", "STATUS_OPERACIONAL", "ARQUITETURA", "FABRICANTE", "ENDERECO_IP", "MODELO"]].to_csv(
    "desafiosdw23/equipamentos_transformados.csv", index=False, sep=";", encoding="UTF-8"
)
