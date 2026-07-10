import os
import tomllib


def test_project_declares_required_dependencies():
    root = os.path.dirname(os.path.dirname(__file__))
    pyproject = os.path.join(root, 'pyproject.toml')
    assert os.path.exists(pyproject), 'pyproject.toml no encontrado'

    with open(pyproject, 'rb') as fh:
        data = tomllib.load(fh)
    deps = data.get('project', {}).get('dependencies', []) or []
    normalized = [d.split('>=')[0].split('>')[0].split('<')[0].strip().lower() for d in deps]

    required_packages = ['playwright', 'pandas', 'openpyxl']
    for package in required_packages:
        assert package in normalized, f'El paquete {package} no está declarado en pyproject.toml'


