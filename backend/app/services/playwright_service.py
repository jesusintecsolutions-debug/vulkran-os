"""VULKRAN OS — Playwright web automation service.

Capabilities:
- Screenshot capture
- Web scraping with selectors
- SEO analysis
- Competitor research
- Lead enrichment from public web data
"""

import logging
import uuid
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SCREENSHOTS_DIR = Path(settings.data_dir) / "screenshots"


async def take_screenshot(url: str, full_page: bool = True) -> dict:
    """Capture a screenshot of a web page."""
    from playwright.async_api import async_playwright

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"screenshot_{uuid.uuid4().hex[:10]}.png"
    output_path = SCREENSHOTS_DIR / filename

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.screenshot(path=str(output_path), full_page=full_page)
        title = await page.title()
        await browser.close()

    logger.info("Screenshot captured: %s → %s", url, filename)

    return {
        "url": url,
        "title": title,
        "screenshot_path": str(output_path),
        "screenshot_url": f"/data/screenshots/{filename}",
    }


async def scrape_page(url: str, selectors: dict[str, str] | None = None) -> dict:
    """
    Scrape structured data from a web page.

    Args:
        url: Target URL
        selectors: Dict of {field_name: css_selector} to extract

    Returns:
        Dict with extracted data
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=30000, wait_until="networkidle")

        data = {
            "url": url,
            "title": await page.title(),
        }

        if selectors:
            for field, selector in selectors.items():
                try:
                    elements = await page.query_selector_all(selector)
                    texts = []
                    for el in elements:
                        text = await el.text_content()
                        if text:
                            texts.append(text.strip())
                    data[field] = texts if len(texts) > 1 else (texts[0] if texts else None)
                except Exception as e:
                    data[field] = f"Error: {e}"
        else:
            # Default: extract main text content
            data["text"] = await page.evaluate("""
                () => document.body.innerText.substring(0, 5000)
            """)

        await browser.close()

    return data


async def analyze_seo(url: str) -> dict:
    """Perform SEO analysis of a web page."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        start_time = __import__("time").time()
        await page.goto(url, timeout=30000, wait_until="networkidle")
        load_time = __import__("time").time() - start_time

        seo_data = await page.evaluate("""
            () => {
                const getMeta = (name) => {
                    const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                    return el ? el.getAttribute('content') : null;
                };
                const headings = {};
                ['h1','h2','h3'].forEach(tag => {
                    headings[tag] = Array.from(document.querySelectorAll(tag))
                        .map(el => el.textContent.trim())
                        .filter(Boolean);
                });
                const images = Array.from(document.querySelectorAll('img'));
                const imagesWithoutAlt = images.filter(img => !img.alt).length;
                const links = document.querySelectorAll('a[href]');
                const internalLinks = Array.from(links).filter(a =>
                    a.href.startsWith(window.location.origin)
                ).length;
                const externalLinks = links.length - internalLinks;

                return {
                    title: document.title,
                    title_length: document.title.length,
                    description: getMeta('description'),
                    description_length: (getMeta('description') || '').length,
                    og_title: getMeta('og:title'),
                    og_description: getMeta('og:description'),
                    og_image: getMeta('og:image'),
                    canonical: document.querySelector('link[rel="canonical"]')?.href || null,
                    robots: getMeta('robots'),
                    headings,
                    total_images: images.length,
                    images_without_alt: imagesWithoutAlt,
                    internal_links: internalLinks,
                    external_links: externalLinks,
                    word_count: document.body.innerText.split(/\\s+/).length,
                    has_structured_data: !!document.querySelector('script[type="application/ld+json"]'),
                };
            }
        """)

        seo_data["url"] = url
        seo_data["load_time_seconds"] = round(load_time, 2)

        # Scoring
        score = 100
        issues = []
        if not seo_data.get("title") or seo_data["title_length"] > 60:
            score -= 10
            issues.append("Title missing or too long (>60 chars)")
        if not seo_data.get("description") or seo_data["description_length"] > 160:
            score -= 10
            issues.append("Meta description missing or too long (>160 chars)")
        if not seo_data.get("og_image"):
            score -= 5
            issues.append("Missing og:image")
        if seo_data.get("images_without_alt", 0) > 0:
            score -= 5
            issues.append(f"{seo_data['images_without_alt']} images without alt text")
        if not seo_data.get("has_structured_data"):
            score -= 5
            issues.append("No structured data (JSON-LD)")
        if load_time > 3:
            score -= 10
            issues.append(f"Slow load time: {load_time:.1f}s")
        if not seo_data.get("headings", {}).get("h1"):
            score -= 10
            issues.append("Missing H1 heading")

        seo_data["seo_score"] = max(score, 0)
        seo_data["issues"] = issues

        await browser.close()

    return seo_data


async def enrich_lead(company_url: str) -> dict:
    """Enrich lead data by scraping public company info."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(company_url, timeout=30000, wait_until="networkidle")

            data = await page.evaluate("""
                () => {
                    const getMeta = (name) => {
                        const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                        return el ? el.getAttribute('content') : null;
                    };
                    // Try to find contact info
                    const text = document.body.innerText;
                    const emailMatch = text.match(/[\\w.-]+@[\\w.-]+\\.\\w+/);
                    const phoneMatch = text.match(/(?:\\+34|0034)?\\s*[6789]\\d{2}[\\s.-]?\\d{3}[\\s.-]?\\d{3}/);

                    return {
                        title: document.title,
                        description: getMeta('description'),
                        og_title: getMeta('og:title'),
                        email: emailMatch ? emailMatch[0] : null,
                        phone: phoneMatch ? phoneMatch[0].replace(/\\s/g, '') : null,
                        social_links: Array.from(document.querySelectorAll('a[href]'))
                            .map(a => a.href)
                            .filter(h => /linkedin|twitter|instagram|facebook|youtube/.test(h))
                            .slice(0, 5),
                    };
                }
            """)

            data["url"] = company_url
            data["scraped"] = True

        except Exception as e:
            data = {"url": company_url, "error": str(e), "scraped": False}

        await browser.close()

    return data
