from playwright.sync_api import sync_playwright
import pandas as pd
import time
import re
import os
from datetime import datetime
from config import HEADLESS, SITIOS, URLS, EXCEL_COMBINADO, EXCEL_COMBINADO_FILENAME, MODO, DEBUG


class WorldClassScraper:
    def __init__(self, base_url, email, password, headless=True):
        self.base_url = base_url
        self.email = email
        self.password = password
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None

    # ─────────────────────────────────────────────
    # NAVEGADOR
    # ─────────────────────────────────────────────

    def iniciar_navegador(self):
        print(f"→ Iniciando navegador (headless={self.headless})...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        print("✓ Navegador iniciado")

    def cerrar_navegador(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("✓ Navegador cerrado")

    def _goto(self, url, reintentos=3, espera=10):
        for intento in range(1, reintentos + 1):
            try:
                self.page.goto(url)
                self.page.wait_for_load_state('networkidle')
                return
            except Exception as e:
                if 'net::ERR_' in str(e) and intento < reintentos:
                    print(f"  ⚠ Error de red (intento {intento}/{reintentos}), esperando {espera}s...")
                    time.sleep(espera)
                else:
                    raise

    # ─────────────────────────────────────────────
    # LOGIN
    # ─────────────────────────────────────────────

    def login(self):
        print(f"→ Navegando a login: {self.base_url}{URLS['login']}")
        self._goto(f"{self.base_url}{URLS['login']}")
        self.page.fill('input[type="email"], input#email', self.email)
        self.page.fill('input[type="password"], input#password', self.password)
        self.page.click('button[type="submit"], input[type="submit"]')
        self.page.wait_for_load_state('networkidle')

        if 'login' not in self.page.url.lower():
            print("✓ Login exitoso")
            return True
        else:
            self.page.screenshot(path='login_error.png')
            print("✗ Login fallido — screenshot guardado en login_error.png")
            return False

    # ─────────────────────────────────────────────
    # APLICAR FILTROS
    # ─────────────────────────────────────────────

    def _aplicar_filtros_en_pagina(self, filtros, estado):
        # Sede — solo si está configurada
        if filtros.get('sede'):
            self.page.select_option('select#bus_sede', label=filtros['sede'])
            time.sleep(0.3)

        # Fechas via JS para evitar problemas con input[type=date]
        for selector, valor in [('input#bus_f1', filtros['fecha_inicial']),
                                 ('input#bus_f2', filtros['fecha_final'])]:
            self.page.evaluate(f"""() => {{
                const el = document.querySelector('{selector}');
                if (el) {{
                    el.value = '{valor}';
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}
            }}""")
        time.sleep(0.3)

        self.page.select_option('select#bus_estado', label=estado)
        time.sleep(0.3)

        f1 = self.page.locator('input#bus_f1').first.input_value()
        f2 = self.page.locator('input#bus_f2').first.input_value()
        print(f"  • Fecha inicial: '{f1}' | Fecha final: '{f2}'")

        boton = self.page.locator('button[onclick*="buscarXcs"]')
        if boton.count() == 0:
            boton = self.page.locator('button:has-text("Buscar")')
        if boton.count() == 0:
            boton = self.page.locator('button[type="submit"]')

        if boton.count() > 0:
            boton.first.click()
            print("  → Botón Buscar clickeado")
        else:
            print("  ⚠ No se encontró botón Buscar")

        self.page.wait_for_load_state('networkidle')
        time.sleep(2)

    # ─────────────────────────────────────────────
    # RECOLECTAR URLs (con paginación por clic)
    # ─────────────────────────────────────────────

    def _recolectar_urls_contratos(self, estado):
        urls = []
        pagina = 1

        while True:
            print(f"  → Página {pagina}: recolectando enlaces...")
            enlaces = self.page.locator('a[href*="/vercontrato/"]').all()
            print(f"    → {len(enlaces)} contratos encontrados")

            for enlace in enlaces:
                try:
                    href = enlace.get_attribute('href')
                    if not href:
                        continue
                    url = href if href.startswith('http') else f"{self.base_url}{href}"
                    if url not in urls:
                        urls.append(url)
                except:
                    continue

            if pagina == 1 and DEBUG:
                self.page.screenshot(path=f'debug_paginacion_{estado}.png')

            siguiente = self.page.locator('ul.pagination li:not(.disabled) a[rel="next"]')
            if siguiente.count() == 0:
                print(f"  ✓ Fin de paginación ({pagina} página(s), {len(urls)} contratos)")
                break

            print(f"    → Navegando a página {pagina + 1}...")
            siguiente.first.click()
            self.page.wait_for_load_state('networkidle')
            time.sleep(1.5)
            pagina += 1

        return urls

    # ─────────────────────────────────────────────
    # EXTRAER DETALLE DE UN CONTRATO
    # ─────────────────────────────────────────────

    def _extraer_detalle(self, url, estado):
        self._goto(url)
        time.sleep(1.5)

        datos = {}
        texto = self.page.locator('body').text_content()

        # Guardar HTML del primer contrato para debug (una sola vez)
        if DEBUG:
            debug_path = f'debug_detalle_{url.split("/")[-1]}.html'
            if not os.path.exists(debug_path):
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(self.page.content())
                print(f"  [DEBUG] HTML guardado en {debug_path}")

        # ── Número de contrato ──────────────────────────────────────────────
        # Leer del card-header: <strong>Contrato <i>"WCG1234"</i></strong>
        try:
            numero = self.page.evaluate('''() => {
                // Opción 1: card-header con <strong>
                const header = document.querySelector('.card-header strong');
                if (header) {
                    const m = header.textContent.match(/([A-Z]{2,6}\\d+)/i);
                    if (m) return m[1].toUpperCase();
                }
                // Opción 2: cualquier <strong> que contenga "Contrato"
                const strongs = Array.from(document.querySelectorAll('strong'));
                for (const s of strongs) {
                    if (s.textContent.includes('Contrato')) {
                        const m = s.textContent.match(/([A-Z]{2,6}\\d+)/i);
                        if (m) return m[1].toUpperCase();
                    }
                }
                // Opción 3: título de la página
                const m2 = document.title.match(/([A-Z]{2,6}\\d+)/i);
                if (m2) return m2[1].toUpperCase();
                return '';
            }''')
            datos['Numero_Contrato'] = numero or ''
            if not datos['Numero_Contrato'] and DEBUG:
                debug_nc = f'debug_sin_numero_{url.split("/")[-1]}.html'
                if not os.path.exists(debug_nc):
                    with open(debug_nc, 'w', encoding='utf-8') as f:
                        f.write(self.page.content())
                    print(f"  ⚠ Número no encontrado — HTML guardado en {debug_nc}")
        except:
            datos['Numero_Contrato'] = ''

        # ── Fecha de creación ───────────────────────────────────────────────
        try:
            meses = {'ENERO':1,'FEBRERO':2,'MARZO':3,'ABRIL':4,'MAYO':5,'JUNIO':6,
                     'JULIO':7,'AGOSTO':8,'SEPTIEMBRE':9,'OCTUBRE':10,'NOVIEMBRE':11,'DICIEMBRE':12}
            m = re.search(r'Fecha de Creacion[:\s]+([^\n]+)', texto, re.IGNORECASE)
            if m:
                mf = re.search(r'(\d+)\s+DE\s+(\w+)\s+DE\s+(\d+)', m.group(1), re.IGNORECASE)
                if mf:
                    d, mes_n, a = int(mf.group(1)), mf.group(2).upper(), int(mf.group(3))
                    datos['Fecha_Creacion'] = f"{d:02d}/{meses.get(mes_n,1):02d}/{a % 100:02d}"
                else:
                    datos['Fecha_Creacion'] = m.group(1).strip()
            else:
                datos['Fecha_Creacion'] = ''
        except:
            datos['Fecha_Creacion'] = ''

        datos['Estado_Contrato'] = estado

        # ── Titular ─────────────────────────────────────────────────────────
        for campo, placeholder, idx in [
            ('Nombre_Titular',   'Nombre',   0),
            ('Apellido_Titular', 'Apellido', 0),
            ('Cedula_Titular',   'Cedula',   0),
            ('Celular_Titular',  'Celular',  0),
            ('Email_Titular',    'eMail',    0),
        ]:
            try:
                inputs = self.page.locator(f'input[placeholder="{placeholder}"]').all()
                datos[campo] = inputs[idx].input_value(timeout=2000) if len(inputs) > idx else ''
            except:
                datos[campo] = ''

        # ── Cotitular ───────────────────────────────────────────────────────
        for campo, placeholder, idx in [
            ('Nombre_Cotitular',   'Nombre',   1),
            ('Apellido_Cotitular', 'Apellido', 1),
            ('Cedula_Cotitular',   'Cedula',   1),
            ('Celular_Cotitular',  'Celular',  1),
            ('Email_Cotitular',    'eMail',    1),
        ]:
            try:
                inputs = self.page.locator(f'input[placeholder="{placeholder}"]').all()
                datos[campo] = inputs[idx].input_value(timeout=2000) if len(inputs) > idx else ''
            except:
                datos[campo] = ''

        # ── Valor del contrato ──────────────────────────────────────────────
        try:
            m = re.search(r'Valor\s*(?:del\s*contrato)?[:\s]+\$?\s*([0-9,\.]+)', texto, re.IGNORECASE)
            datos['Valor_Contrato'] = m.group(1).strip() if m else ''
        except:
            datos['Valor_Contrato'] = ''

        # ── Cuota inicial ───────────────────────────────────────────────────
        try:
            val = self.page.evaluate('''() => {
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
        except:
            datos['Cuota_Inicial'] = ''

        # ── Pago inicial (Total) ────────────────────────────────────────────
        try:
            m = re.search(r'Total:\s*\$?\s*([0-9,\.]+)', texto, re.IGNORECASE)
            datos['Pago_Inicial'] = m.group(1).strip() if m else ''
        except:
            datos['Pago_Inicial'] = ''

        # ── Financiar Saldo Inicial y Restante ──────────────────────────────
        try:
            resultado = self.page.evaluate('''() => {
                function seccion(texto) {
                    const strongs = Array.from(document.querySelectorAll('strong'));
                    for (const s of strongs) {
                        if (s.textContent.includes(texto)) {
                            let p = s.parentElement;
                            for (let i = 0; i < 10; i++) {
                                if (!p) break;
                                const num  = p.querySelector('input[type="number"]');
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
            datos['Cuotas_Saldo_Inicial']      = resultado['inicial']['cuotas']
            datos['Fecha_Primer_Pago_Inicial']  = resultado['inicial']['fecha']
            datos['Cuotas_Saldo_Restante']      = resultado['restante']['cuotas']
            datos['Fecha_Primer_Pago_Restante'] = resultado['restante']['fecha']
        except:
            datos['Cuotas_Saldo_Inicial']      = ''
            datos['Fecha_Primer_Pago_Inicial']  = ''
            datos['Cuotas_Saldo_Restante']      = ''
            datos['Fecha_Primer_Pago_Restante'] = ''

        datos['url'] = url

        # Log
        print(f"    {datos.get('Numero_Contrato','?')} | {datos.get('Fecha_Creacion','?')} | "
              f"{datos.get('Nombre_Titular','')} {datos.get('Apellido_Titular','')} | "
              f"Ced: {datos.get('Cedula_Titular','')}")
        print(f"    Valor: ${datos.get('Valor_Contrato','?')} | "
              f"Cuota ini: ${datos.get('Cuota_Inicial','?')} | Pago ini: ${datos.get('Pago_Inicial','?')}")
        print(f"    Saldo Ini: {datos.get('Cuotas_Saldo_Inicial','?')} cuotas, "
              f"F.Pago: {datos.get('Fecha_Primer_Pago_Inicial','?')}")
        print(f"    Saldo Res: {datos.get('Cuotas_Saldo_Restante','?')} cuotas, "
              f"F.Pago: {datos.get('Fecha_Primer_Pago_Restante','?')}")

        if any([datos.get('Numero_Contrato'), datos.get('Nombre_Titular'), datos.get('Cedula_Titular')]):
            return datos
        return None

    # ─────────────────────────────────────────────
    # EXPORTAR EXCEL
    # ─────────────────────────────────────────────

    def export_to_excel(self, data, filename):
        if not data:
            print("✗ No hay datos para exportar")
            return

        if os.path.exists(filename):
            try:
                with open(filename, 'a'):
                    pass
            except PermissionError:
                base, ext = filename.rsplit('.', 1)
                filename = f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                print(f"⚠ Archivo en uso, guardando como: {filename}")

        columnas = [
            'sitio',
            'Numero_Contrato', 'Fecha_Creacion', 'Estado_Contrato',
            'Nombre_Titular', 'Apellido_Titular', 'Cedula_Titular', 'Celular_Titular', 'Email_Titular',
            'Nombre_Cotitular', 'Apellido_Cotitular', 'Cedula_Cotitular', 'Celular_Cotitular', 'Email_Cotitular',
            'Valor_Contrato', 'Cuota_Inicial', 'Pago_Inicial',
            'Cuotas_Saldo_Inicial', 'Fecha_Primer_Pago_Inicial',
            'Cuotas_Saldo_Restante', 'Fecha_Primer_Pago_Restante',
            'url'
        ]
        df = pd.DataFrame(data)
        cols = [c for c in columnas if c in df.columns]
        df = df[cols]
        df.to_excel(filename, index=False)
        print(f"✓ Excel guardado: {filename} ({len(df)} registros, {len(df.columns)} columnas)")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("WORLD CLASS SCRAPER - Extracción de Contratos")
    print("=" * 60)

    if MODO == 'todos':
        sitios_a_procesar = SITIOS
    else:
        sitios_a_procesar = [s for s in SITIOS if s['nombre'] == MODO]
        if not sitios_a_procesar:
            print(f"✗ Sitio '{MODO}' no encontrado en SITIOS. Verifica config.py.")
            return

    print(f"\n→ Modo: {MODO.upper()} ({len(sitios_a_procesar)} sitio(s))")

    datos_globales = []

    for sitio in sitios_a_procesar:
        nombre   = sitio['nombre']
        base_url = sitio['base_url']
        filtros  = sitio['filtros']

        print(f"\n{'#'*60}")
        print(f"  SITIO: {nombre.upper()}  ({base_url})")
        print(f"{'#'*60}")

        scraper = WorldClassScraper(base_url, sitio['email'], sitio['password'], headless=HEADLESS)
        datos_sitio = []

        try:
            scraper.iniciar_navegador()

            print("\n[PASO 1] Login...")
            if not scraper.login():
                print(f"✗ Login fallido para {nombre}, saltando sitio.")
                scraper.cerrar_navegador()
                continue
            time.sleep(2)

            for idx, estado in enumerate(filtros['estados'], 1):
                print(f"\n{'='*60}")
                print(f"[{idx}/{len(filtros['estados'])}] Estado: {estado}")
                print(f"{'='*60}")

                scraper._goto(f"{base_url}{URLS['contratos']}")
                time.sleep(1)

                print("→ Aplicando filtros...")
                scraper._aplicar_filtros_en_pagina(filtros, estado)

                print("→ Recolectando contratos...")
                urls = scraper._recolectar_urls_contratos(estado)

                if not urls:
                    print(f"  ℹ No se encontraron contratos para {estado}")
                    continue

                print(f"\n→ Extrayendo detalle de {len(urls)} contratos...")
                for i, url in enumerate(urls, 1):
                    print(f"\n  [{i}/{len(urls)}] Procesando contrato...")
                    try:
                        datos = scraper._extraer_detalle(url, estado)
                        if datos:
                            datos['sitio'] = nombre
                            datos_sitio.append(datos)
                            datos_globales.append(datos)
                            print("  ✓ Datos extraídos")
                        else:
                            print("  ⚠ Sin datos útiles")
                    except Exception as e:
                        print(f"  ✗ Error: {str(e)}")

                n = len([d for d in datos_sitio if d.get('Estado_Contrato') == estado])
                print(f"\n✓ {estado}: {n} contratos extraídos")

        except Exception as e:
            print(f"✗ Error procesando {nombre}: {str(e)}")
        finally:
            scraper.cerrar_navegador()

        print(f"\n→ Exportando Excel de {nombre}...")
        scraper.export_to_excel(datos_sitio, sitio['excel'])

    if MODO == 'todos' and EXCEL_COMBINADO and datos_globales:
        print(f"\n{'='*60}")
        print(f"→ Exportando Excel combinado ({len(datos_globales)} registros)...")
        WorldClassScraper('', '', '').export_to_excel(datos_globales, EXCEL_COMBINADO_FILENAME)

    print(f"\n{'='*60}")
    print("✓ PROCESO COMPLETADO")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
