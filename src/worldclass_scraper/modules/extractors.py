import os
import re
import unicodedata
from typing import Dict, Optional
from playwright.async_api import Page


class ContractExtractor:
    def __init__(self, output_dir: str, debug: bool = False):
        self.output_dir = output_dir
        self.debug = debug

    async def _input_value(self, page: Page, selector: str, index: int = 0) -> str:
        handles = await page.query_selector_all(selector)
        if len(handles) > index:
            try:
                return await handles[index].input_value()
            except Exception:
                return ''
        return ''

    def _normalize_text(self, value: str) -> str:
        if not value:
            return ''
        text = str(value).strip().upper()
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r'\s+', ' ', text)
        return text

    def _normalize_estado(self, estado: str) -> str:
        normalized = self._normalize_text(estado)
        mapping = {
            'PROCESO': 'PROCE',
            'PROCE.': 'PROCE',
            'PROCE': 'PROCE',
            'PROCES': 'PROCE',
            'CASH': 'CASH',
            'EFECTIVO': 'CASH',
            'CERO': 'CERO',
            'ZERO': 'CERO',
            'GASTOLEGAL': 'GASTO LEGAL',
            'GASTO LEGAL': 'GASTO LEGAL',
            'GASTO': 'GASTO LEGAL',
            'SEPARACION': 'SEPARACION',
            'PEDDING': 'PEDDING',
            'PENDING': 'PEDDING',
            'PENDIENTE': 'PEDDING',
        }
        return mapping.get(normalized, normalized)

    def _normalize_sede(self, sede: str) -> str:
        normalized = self._normalize_text(sede)
        if not normalized:
            return ''

        sede_prefixes = {
            'WC': 'WC - SANTO DOMINGO',
            'WC-': 'WC- - GUAYAQUIL',
            'WCG': 'WCG - GUAYAQUIL',
            'WN': 'WN - WORLDCLASS NORTE',
            'OCN': 'OCN - NASELLORIL',
            'WCS': 'WCS - OCT HOTELS',
            'WCQ': 'WCQ - LOS CUATES',
            'WCU': 'WCU - RESTAURANTE',
        }

        for prefix, canonical in sede_prefixes.items():
            if normalized.startswith(prefix) and prefix != 'WC':
                return canonical
            if prefix == 'WC' and normalized.startswith('WC ') and 'SANTO DOMINGO' in normalized:
                return canonical

        # if no known prefix matched, return the normalized label as-is
        return normalized

    async def _textarea_value_by_label(self, page: Page, label_text: str) -> str:
        try:
            return await page.evaluate(f'''() => {{
                const groups = Array.from(document.querySelectorAll('.form-group'));
                for (const group of groups) {{
                    if (group.textContent.includes('{label_text}')) {{
                        const textarea = group.querySelector('textarea');
                        if (textarea) return textarea.value.trim();
                    }}
                }}
                const textarea = document.querySelector('textarea');
                return textarea ? textarea.value.trim() : '';
            }}''')
        except Exception:
            return ''

    async def _extract_comments_from_table(self, page: Page) -> str:
        try:
            return await page.evaluate(r'''() => {
                function normalize(text) {
                    return text ? text.toString().trim().replace(/\s+/g, ' ') : '';
                }

                const tables = Array.from(document.querySelectorAll('table'));
                for (const table of tables) {
                    const headers = Array.from(table.querySelectorAll('thead th')).map(th => normalize(th.textContent).toUpperCase());
                    if (!headers.some(h => h.includes('COMENTARIO'))) continue;

                    const commentIndex = headers.findIndex(h => h.includes('COMENTARIO'));
                    const rows = Array.from(table.querySelectorAll('tbody tr'));
                    const comments = [];
                    for (const row of rows) {
                        const cells = Array.from(row.querySelectorAll('td'));
                        if (!cells.length) continue;
                        let cell = null;
                        if (commentIndex >= 0 && commentIndex < cells.length) {
                            cell = cells[commentIndex];
                        } else {
                            cell = cells[cells.length - 1];
                        }
                        const value = normalize(cell.textContent);
                        if (value) comments.push(value);
                    }
                    if (comments.length) {
                        return comments.join(' | ');
                    }
                }
                return '';
            }''')
        except Exception:
            return ''

    async def extract(self, page: Page, url: str, estado: str, sede: str = '') -> Optional[Dict[str, str]]:
        datos: Dict[str, str] = {}
        texto = await page.locator('body').text_content() or ''

        try:
            numero = await page.evaluate(r'''() => {
                const header = document.querySelector('.card-header strong');
                if (header) {
                    const m = header.textContent.match(/([A-Z]{2,6}\d+)/i);
                    if (m) return m[1].toUpperCase();
                }
                const strongs = Array.from(document.querySelectorAll('strong'));
                for (const s of strongs) {
                    if (s.textContent.includes('Contrato')) {
                        const m = s.textContent.match(/([A-Z]{2,6}\d+)/i);
                        if (m) return m[1].toUpperCase();
                    }
                }
                const m2 = document.title.match(/([A-Z]{2,6}\d+)/i);
                if (m2) return m2[1].toUpperCase();
                return '';
            }''')
            datos['Numero_Contrato'] = numero or ''
        except Exception:
            datos['Numero_Contrato'] = ''

        try:
            meses = {
                'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4, 'MAYO': 5, 'JUNIO': 6,
                'JULIO': 7, 'AGOSTO': 8, 'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12,
            }
            m = re.search(r'Fecha de Creacion[:\s]+([^\n]+)', texto, re.IGNORECASE)
            if m:
                mf = re.search(r'(\d+)\s+DE\s+(\w+)\s+DE\s+(\d+)', m.group(1), re.IGNORECASE)
                if mf:
                    d, mes_n, a = int(mf.group(1)), mf.group(2).upper(), int(mf.group(3))
                    datos['Fecha_Creacion'] = f"{d:02d}/{meses.get(mes_n, 1):02d}/{a % 100:02d}"
                else:
                    datos['Fecha_Creacion'] = m.group(1).strip()
            else:
                datos['Fecha_Creacion'] = ''
        except Exception:
            datos['Fecha_Creacion'] = ''

        datos['Sede'] = self._normalize_sede(sede)
        datos['Estado_Contrato'] = self._normalize_estado(estado)

        for campo, placeholder, idx in [
            ('Nombre_Titular', 'Nombre', 0),
            ('Apellido_Titular', 'Apellido', 0),
            ('Cedula_Titular', 'Cedula', 0),
            ('Celular_Titular', 'Celular', 0),
            ('Email_Titular', 'eMail', 0),
        ]:
            datos[campo] = await self._input_value(page, f'input[placeholder="{placeholder}"]', idx)

        for campo, placeholder, idx in [
            ('Nombre_Cotitular', 'Nombre', 1),
            ('Apellido_Cotitular', 'Apellido', 1),
            ('Cedula_Cotitular', 'Cedula', 1),
            ('Celular_Cotitular', 'Celular', 1),
            ('Email_Cotitular', 'eMail', 1),
        ]:
            datos[campo] = await self._input_value(page, f'input[placeholder="{placeholder}"]', idx)

        try:
            m = re.search(r'Valor\s*(?:del\s*contrato)?[:\s]+\$?\s*([0-9,\.]+)', texto, re.IGNORECASE)
            datos['Valor_Contrato'] = m.group(1).strip() if m else ''
        except Exception:
            datos['Valor_Contrato'] = ''

        try:
            val = await page.evaluate('''() => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let node;
                while (node = walker.nextNode()) {
                    if (node.textContent.trim() === 'Cuota Inicial') {
                        let p = node.parentElement;
                        for (let i = 0; i < 5; i++) {
                            if (!p || p.tagName === 'BODY') break;
                            const inp = p.querySelector('input[type="number"]');
                            if (inp && inp.value) return inp.value;
                            p = p.parentElement;
                        }
                    }
                }
                return '';
            }''')
            datos['Cuota_Inicial'] = val
        except Exception:
            datos['Cuota_Inicial'] = ''

        try:
            m = re.search(r'Total:\s*\$?\s*([0-9,\.]+)', texto, re.IGNORECASE)
            datos['Pago_Inicial'] = m.group(1).strip() if m else ''
        except Exception:
            datos['Pago_Inicial'] = ''

        try:
            resultado = await page.evaluate('''() => {
                function seccion(texto) {
                    const strongs = Array.from(document.querySelectorAll('strong'));
                    for (const s of strongs) {
                        if (s.textContent.includes(texto)) {
                            let p = s.parentElement;
                            for (let i = 0; i < 10; i++) {
                                if (!p) break;
                                const num = p.querySelector('input[type="number"]');
                                const date = p.querySelector('input[type="date"]');
                                if (num && date) return { cuotas: num.value || '', fecha: date.value || '' };
                                p = p.parentElement;
                            }
                        }
                    }
                    return { cuotas: '', fecha: '' };
                }
                return { inicial: seccion('Saldo Inicial'), restante: seccion('Saldo Restante') };
            }''')
            datos['Cuotas_Saldo_Inicial'] = resultado['inicial']['cuotas']
            datos['Fecha_Primer_Pago_Inicial'] = resultado['inicial']['fecha']
            datos['Cuotas_Saldo_Restante'] = resultado['restante']['cuotas']
            datos['Fecha_Primer_Pago_Restante'] = resultado['restante']['fecha']
        except Exception:
            datos['Cuotas_Saldo_Inicial'] = ''
            datos['Fecha_Primer_Pago_Inicial'] = ''
            datos['Cuotas_Saldo_Restante'] = ''
            datos['Fecha_Primer_Pago_Restante'] = ''

        comentario_text = await self._textarea_value_by_label(page, 'Comentario')
        if comentario_text:
            datos['Comentario'] = comentario_text
        else:
            datos['Comentario'] = await self._extract_comments_from_table(page)
        datos['url'] = url

        if any([datos.get('Numero_Contrato'), datos.get('Nombre_Titular'), datos.get('Cedula_Titular')]):
            return datos

        return None
