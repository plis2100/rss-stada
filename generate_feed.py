import html
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright


SOURCE_URL = "https://www.stada.com/media/press-releases/2026"
BASE_URL = "https://www.stada.com"
OUTPUT_FILE = Path("docs/feed.xml")


def limpiar(texto):
    return " ".join((texto or "").split())


def obtener_noticias():
    noticias = {}

    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=True)

        pagina = navegador.new_page(
            viewport={"width": 1440, "height": 1200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
            ),
        )

        pagina.goto(
            SOURCE_URL,
            wait_until="domcontentloaded",
            timeout=90000
        )

        pagina.wait_for_timeout(12000)
        pagina.evaluate(
            "window.scrollTo(0, document.body.scrollHeight)"
        )
        pagina.wait_for_timeout(5000)

        enlaces = pagina.locator(
            'a[href*="/media/press-releases/2026/"]'
        )

        for indice in range(enlaces.count()):
            elemento = enlaces.nth(indice)

            href = elemento.get_attribute("href")
            titulo = limpiar(elemento.inner_text())

            if not href or not titulo or len(titulo) < 15:
                continue

            enlace = urljoin(BASE_URL, href)
            enlace = enlace.split("?")[0].split("#")[0]

            try:
                bloque = elemento.locator(
                    "xpath=ancestor::*[self::article or self::li "
                    "or contains(@class,'card')][1]"
                )

                texto_bloque = limpiar(bloque.inner_text())
            except Exception:
                texto_bloque = titulo

            coincidencia = re.search(
                r"(\d{1,2})[./\s-]+"
                r"(January|February|March|April|May|June|July|"
                r"August|September|October|November|December)"
                r"[,\s]+(2026)",
                texto_bloque,
                re.IGNORECASE
            )

            if coincidencia:
                try:
                    fecha = datetime.strptime(
                        " ".join(coincidencia.groups()),
                        "%d %B %Y"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    fecha = datetime.now(timezone.utc)
            else:
                fecha = datetime.now(timezone.utc)

            noticias[enlace] = {
                "title": titulo,
                "link": enlace,
                "date": fecha,
            }

        navegador.close()

    if not noticias:
        raise RuntimeError(
            "No se encontraron comunicados de STADA. "
            "La RSS anterior no será eliminada."
        )

    return sorted(
        noticias.values(),
        key=lambda noticia: noticia["date"],
        reverse=True
    )


def crear_rss(noticias):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    ahora = format_datetime(datetime.now(timezone.utc))

    contenido = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        '<rss version="2.0" '
        'xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        "    <title>STADA - Press Releases</title>",
        f"    <link>{html.escape(SOURCE_URL)}</link>",
        (
            "    <description>Últimos comunicados de prensa "
            "publicados por STADA</description>"
        ),
        "    <language>en</language>",
        f"    <lastBuildDate>{html.escape(ahora)}</lastBuildDate>",
        (
            '    <atom:link href="feed.xml" rel="self" '
            'type="application/rss+xml"/>'
        ),
    ]

    for noticia in noticias[:80]:
        contenido.extend([
            "    <item>",
            f"      <title>{html.escape(noticia['title'])}</title>",
            f"      <link>{html.escape(noticia['link'])}</link>",
            (
                '      <guid isPermaLink="true">'
                f"{html.escape(noticia['link'])}</guid>"
            ),
            (
                "      <description>Comunicado de prensa "
                "publicado por STADA.</description>"
            ),
            (
                f"      <pubDate>"
                f"{html.escape(format_datetime(noticia['date']))}"
                f"</pubDate>"
            ),
            "    </item>",
        ])

    contenido.extend([
        "  </channel>",
        "</rss>",
        "",
    ])

    OUTPUT_FILE.write_text(
        "\n".join(contenido),
        encoding="utf-8"
    )

    print(f"RSS creada con {len(noticias[:80])} comunicados.")


if __name__ == "__main__":
    crear_rss(obtener_noticias())
