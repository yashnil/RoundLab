"""Optional GROBID integration for structured scholarly PDF extraction.

GROBID is a machine-learning library for extracting information from scholarly documents.
Run locally: docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.7.3
Or use a remote server.

All functions gracefully return None/empty when GROBID is unavailable.
"""

import logging
import re
from typing import Optional
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

_TEI_NS = "http://www.tei-c.org/ns/1.0"


def _ns(tag: str) -> str:
    return f"{{{_TEI_NS}}}{tag}"


class GrobidMetadata:
    def __init__(self):
        self.title: str = ""
        self.authors: list[str] = []
        self.year: str = ""
        self.abstract: str = ""
        self.journal: str = ""
        self.doi: str = ""
        self.body_sections: list[str] = []

    @property
    def author_display(self) -> str:
        if not self.authors:
            return ""
        if len(self.authors) == 1:
            return self.authors[0]
        return self.authors[0] + " et al."

    @property
    def full_text(self) -> str:
        parts = []
        if self.abstract:
            parts.append(self.abstract)
        parts.extend(self.body_sections[:10])  # limit to 10 sections
        return "\n\n".join(parts)


def parse_tei_metadata(tei_xml: str) -> GrobidMetadata:
    """Parse GROBID TEI XML into structured metadata.

    Handles malformed XML gracefully.
    """
    meta = GrobidMetadata()
    try:
        root = ET.fromstring(tei_xml)
    except ET.ParseError as e:
        logger.debug("GROBID TEI parse error: %s", e)
        return meta

    header = root.find(f".//{_ns('teiHeader')}")
    if header is None:
        return meta

    # Title
    title_elem = header.find(f".//{_ns('title')}[@level='a']")
    if title_elem is None:
        title_elem = header.find(f".//{_ns('title')}")
    if title_elem is not None and title_elem.text:
        meta.title = title_elem.text.strip()

    # Authors
    for author in header.findall(f".//{_ns('author')}"):
        surname = author.find(f".//{_ns('surname')}")
        forename = author.find(f".//{_ns('forename')}")
        if surname is not None and surname.text:
            name = surname.text.strip()
            if forename is not None and forename.text:
                name = forename.text.strip() + " " + name
            meta.authors.append(name)

    # Year
    date_elem = header.find(f".//{_ns('date')}[@type='published']")
    if date_elem is None:
        date_elem = header.find(f".//{_ns('date')}")
    if date_elem is not None:
        when = date_elem.get("when", "") or (date_elem.text or "")
        m = re.search(r"\b(19|20)\d{2}\b", when)
        if m:
            meta.year = m.group(0)

    # Journal
    journal = header.find(f".//{_ns('title')}[@level='j']")
    if journal is not None and journal.text:
        meta.journal = journal.text.strip()

    # DOI
    for idno in header.findall(f".//{_ns('idno')}"):
        if idno.get("type", "").lower() == "doi" and idno.text:
            meta.doi = idno.text.strip()
            break

    # Abstract
    abstract = root.find(f".//{_ns('abstract')}")
    if abstract is not None:
        texts = " ".join(t.strip() for t in abstract.itertext() if t.strip())
        if texts:
            meta.abstract = texts[:2000]

    # Body sections
    body = root.find(f".//{_ns('body')}")
    if body is not None:
        for div in body.findall(f".//{_ns('div')}"):
            head = div.find(_ns("head"))
            head_text = (head.text or "").strip() if head is not None else ""
            paras = " ".join(
                " ".join(t.strip() for t in p.itertext() if t.strip())
                for p in div.findall(_ns("p"))
            )
            section = (f"{head_text}: {paras}" if head_text else paras).strip()
            if len(section) > 100:
                meta.body_sections.append(section[:3000])

    return meta


def extract_with_grobid(
    pdf_url: str,
    grobid_url: str,
    max_pdf_mb: int = 10,
    timeout: float = 30.0,
) -> Optional[GrobidMetadata]:
    """Download a PDF and send it to GROBID for structured extraction.

    Returns None on any failure — always safe to call.

    grobid_url: e.g. "http://localhost:8070"
    """
    if not pdf_url or not grobid_url:
        return None

    try:
        # Download PDF
        r = httpx.get(pdf_url, timeout=timeout, follow_redirects=True)
        if r.status_code != 200:
            logger.debug("GROBID: PDF download failed %s status=%d", pdf_url[:80], r.status_code)
            return None

        content = r.content
        size_mb = len(content) / (1024 * 1024)
        if size_mb > max_pdf_mb:
            logger.debug("GROBID: PDF too large (%.1fMB > %dMB limit)", size_mb, max_pdf_mb)
            return None

        content_type = r.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not pdf_url.lower().endswith(".pdf"):
            logger.debug("GROBID: URL does not appear to be a PDF")
            return None

        # Send to GROBID
        process_url = grobid_url.rstrip("/") + "/api/processFulltextDocument"
        grobid_resp = httpx.post(
            process_url,
            files={"input": ("document.pdf", content, "application/pdf")},
            timeout=timeout,
        )

        if grobid_resp.status_code != 200:
            logger.debug("GROBID: processing failed status=%d", grobid_resp.status_code)
            return None

        return parse_tei_metadata(grobid_resp.text)

    except Exception as exc:
        logger.debug("GROBID extraction failed for %s: %s", pdf_url[:80], exc)
        return None


def is_pdf_url(url: str) -> bool:
    """Heuristic check if a URL likely points to a PDF."""
    url_lower = url.lower()
    return (
        url_lower.endswith(".pdf")
        or "/pdf/" in url_lower
        or "?type=pdf" in url_lower
        or "format=pdf" in url_lower
        or "download=pdf" in url_lower
        or "/download/" in url_lower
    )
