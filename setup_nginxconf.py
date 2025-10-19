from jinja2 import Environment, FileSystemLoader
import argparse

def setup_nginx(nbots: int) -> None:
    """
    Método responsável por configurar o nginx.conf com o número máximo de instâncias de robôs que serão utilizados.
    """
    env = Environment(loader=FileSystemLoader('nginx-1.28.0/nginx-1.28.0/conf'))
    template = env.get_template('nginx.conf.j2')

    config = template.render(numero_de_robos=nbots)

    with open('.\\nginx-1.28.0\\nginx-1.28.0\\conf\\nginx.conf', 'w') as f:
        f.write(config)

def get_nbots_flag() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--nbots', type=int, help="Número máximo de robôs")
    return parser.parse_args().nbots

if __name__ == '__main__':
    setup_nginx(nbots=get_nbots_flag())