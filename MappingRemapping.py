import os
import re
import shutil
from Constants import abas

pasta = "Mapeamentos"

# Regex para capturar app, mode, action e part (aceitando acentos)
regex = re.compile(
    r"([^\W\d_]+)"       # app
    r"(Active|Passive)"   # mode
    r"([a-z_]+)"          # action
    r"([A-Z][a-zA-Z]*Commands|[A-Z][a-zA-Z]*ReturnCommands|[A-Z][a-zA-Z]*NavCommands|[A-Z][a-zA-Z]*ActCommands)\.txt",
    re.UNICODE
)

def processar_arquivo(arquivo):
    match = regex.match(arquivo)
    if not match:
        return None
    
    app, mode, action, part_sufixo = match.groups()
    
    # Determinar tipo pelo sufixo
    if part_sufixo.endswith("ActCommands"):
        tipo = "Act"
    elif part_sufixo.endswith("NavCommands"):
        tipo = "Nav"
        action = abas.get(action, action)
    elif part_sufixo.endswith("ReturnCommands"):
        tipo = "Ret"
    else:
        return None

    destino_dir = os.path.join(pasta, app, tipo)
    os.makedirs(destino_dir, exist_ok=True)
    
    return os.path.join(destino_dir, f"{action}.txt")

for arquivo in os.listdir(pasta):
    if arquivo.endswith(".txt"):
        destino = processar_arquivo(arquivo)
        if destino:
            shutil.move(os.path.join(pasta, arquivo), destino)
            print(f"{arquivo} movido para {destino}")
        else:
            print(f"{arquivo} não casou com nenhum padrão, ignorado.")
