from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from feedgen.feed import FeedGenerator


SOURCE_URL = "https://www.stada.com/media/press-releases/2026"

API_URL = (
    "https://www.stada.com/api/blog-listing"
    "?page=1"
    "&count=100"
    "&start=c999a866-660a-4586-8ac6-8692e564a165"
)

BASE_URL = "https://www.stada.com"
OUTPUT_FILE = Path("docs/feed.xml")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def convertir_fecha(texto):
    try:
        fecha = datetime.fromisoformat(
            texto.replace("Z", "+00:00")
        )

        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)

        return fecha

    except Exception:
        return datetime.now(timezone.utc)


def obtener_noticias():
    respuesta = requests.get(
        API_URL,
        headers=HEADERS,
        timeout=60
    )

    respuesta.raise_for_status()
    datos = respuesta.json()
    noticias = []

    for elemento in datos.get("results", []):
        titulo = " ".join(
            (elemento.get("title") or "").split()
        )

        enlace = elemento.get("url") or ""
        descripcion = " ".join(
            (elemento.get("description") or "").split()
        )

        fecha = elemento.get("postDate") or ""

        categorias = elemento.get("categories") or []

        if "Press Release" not in categorias:
            continue

        if not titulo or not enlace:
            continue

        enlace = urljoin(BASE_URL, enlace)

        if not descripcion:
            descripcion = (
                "Comunicado de prensa publicado por STADA."
            )

        noticias.append({
            "title": titulo,
            "link": enlace,
            "description": descripcion,
            "date": convertir_fecha(fecha),
        })

    if not noticias:
        raise RuntimeError(
            "La API de STADA no devolvió comunicados."
        )

    return sorted(
        noticias,
        key=lambda noticia: noticia["date"],
        reverse=True
    )


def crear_rss():
    noticias = obtener_noticias()

    feed = FeedGenerator()

    feed.title("STADA - Press Releases")
    feed.link(href=SOURCE_URL, rel="alternate")
    feed.description(
        "Últimos comunicados de prensa publicados por STADA"
    )
    feed.language("en")
    feed.id(SOURCE_URL)
    feed.lastBuildDate(datetime.now(timezone.utc))

    for noticia in reversed(noticias):
        entrada = feed.add_entry()
        entrada.id(noticia["link"])
        entrada.title(noticia["title"])
        entrada.link(href=noticia["link"])
        entrada.description(noticia["description"])
        entrada.pubDate(noticia["date"])

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    feed.rss_file(
        str(OUTPUT_FILE),
        pretty=True
    )

    print(
        f"RSS creada correctamente con "
        f"{len(noticias)} comunicados."
    )


if __name__ == "__main__":
    crear_rss()
