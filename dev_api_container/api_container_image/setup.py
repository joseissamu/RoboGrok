from jinja2 import Environment, FileSystemLoader
import os

NBOTS_default = 3

def setup_nginx(nbots: int = -1) -> None:
    """
    Método responsável por configurar o nginx.conf com o número máximo de instâncias de robôs que serão utilizados.
    """
    env = Environment(loader=FileSystemLoader('/app/nginx_template'))
    template = env.get_template('default.conf.j2')

    if nbots < 0:
        nbots = get_nbots_flag()

    config = template.render(numero_de_robos=nbots)

    with open('/etc/nginx/conf.d/default.conf', 'w') as f:
        f.write(config)

def get_nbots_flag() -> int:
    return int(os.environ.get('NBOTS', default=NBOTS_default))

if __name__ == '__main__':
    setup_nginx()
