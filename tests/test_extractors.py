import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from worldclass_scraper.modules.extractors import ContractExtractor


class FakeLocator:
    def __init__(self, text: str):
        self._text = text

    async def text_content(self) -> str:
        return self._text


class FakePage:
    def __init__(self, body_text: str, textarea_value: str):
        self.body_text = body_text
        self.textarea_value = textarea_value

    def locator(self, selector: str):
        return FakeLocator(self.body_text)

    async def query_selector_all(self, selector: str):
        return []

    async def evaluate(self, expression: str):
        if 'card-header strong' in expression:
            return 'WCG123'
        if 'Cuota Inicial' in expression:
            return '150'
        if 'Saldo Inicial' in expression:
            return {
                'inicial': {'cuotas': '3', 'fecha': '2025-05-01'},
                'restante': {'cuotas': '12', 'fecha': '2025-06-01'},
            }
        if "group.textContent.includes('Comentario')" in expression:
            return self.textarea_value
        if 'findIndex(h => h.includes(\'COMENTARIO\'))' in expression or 'headers.some(h => h.includes(\'COMENTARIO\'))' in expression:
            return 'se deja msj jurídico att casierra | factura #13348'
        return ''


async def _run_extract(estado: str = 'PROCE', sede: str = '', textarea_value: str = 'Este es el comentario'):
    page = FakePage(
        body_text='Fecha de Creacion: 1 DE ENERO DE 2025\nValor del contrato: $1,000.00\nTotal: $200',
        textarea_value=textarea_value,
    )
    extractor = ContractExtractor(output_dir='/tmp')
    return await extractor.extract(page, 'http://example.com/contrato/WCG123', estado, sede)


def test_extract_comentario():
    datos = asyncio.run(_run_extract())

    assert datos is not None
    assert datos['Comentario'] == 'Este es el comentario'
    assert datos['Numero_Contrato'] == 'WCG123'
    assert datos['Estado_Contrato'] == 'PROCE'


def test_extract_comentario_from_table_when_textarea_empty():
    datos = asyncio.run(_run_extract(estado='PROCE', sede='WCG - Guayaquil', textarea_value=''))

    assert datos is not None
    assert datos['Comentario'] == 'se deja msj jurídico att casierra | factura #13348'


def test_normaliza_estado_y_sede():
    datos = asyncio.run(_run_extract(estado='proceso', sede='Wcg - Guayaquil'))

    assert datos is not None
    assert datos['Sede'] == 'WCG - GUAYAQUIL'
    assert datos['Estado_Contrato'] == 'PROCE'


def test_normaliza_sedes_prefijo_wc():
    datos = asyncio.run(_run_extract(estado='PROCE', sede='WC - Santo domingo'))
    assert datos is not None
    assert datos['Sede'] == 'WC - SANTO DOMINGO'

    datos = asyncio.run(_run_extract(estado='PROCE', sede='WC- - Guayaquil'))
    assert datos is not None
    assert datos['Sede'] == 'WC- - GUAYAQUIL'

    datos = asyncio.run(_run_extract(estado='PROCE', sede='WN - worldclass norte'))
    assert datos is not None
    assert datos['Sede'] == 'WN - WORLDCLASS NORTE'

    datos = asyncio.run(_run_extract(estado='PROCE', sede='OCN - NASELLORIL'))
    assert datos is not None
    assert datos['Sede'] == 'OCN - NASELLORIL'
