from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
results = {}
with sync_playwright() as p:
    for name, viewport, mobile in [("desktop", {"width": 1920, "height": 1080}, False), ("mobile_touch_emulation", {"width": 390, "height": 844}, True)]:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport, has_touch=mobile, is_mobile=mobile)
        errors=[]; page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        response=page.goto("http://127.0.0.1:8891/presentation/index.html", wait_until="networkidle")
        page.wait_for_selector(".reveal.ready")
        total=page.locator(".slides > section").count()
        first=page.locator("section.present h1").inner_text()
        if mobile:
            page.touchscreen.tap(360, 420); page.wait_for_timeout(400)
        else:
            page.keyboard.press("ArrowRight"); page.wait_for_timeout(300)
        index=page.evaluate("Reveal.getIndices().h")
        page.evaluate("Reveal.toggleOverview()")
        overview=page.locator(".reveal.overview").count() == 1
        page.evaluate("Reveal.toggleOverview(); Reveal.slide(15)")
        last=page.locator("section.present h2").inner_text()
        overflow=page.evaluate("Math.max(document.documentElement.scrollWidth-innerWidth, document.documentElement.scrollHeight-innerHeight)")
        page.screenshot(path=str(ROOT / f"blackbox_{name}.png"), full_page=True)
        results[name]={"http_status":response.status if response else None,"slide_count":total,"title":first,"navigation_index":index,"overview":overview,"last_slide":last,"console_errors":errors,"viewport_overflow_px":overflow,"status":"PASS" if total==16 and index==1 and overview and not errors else "FAIL"}
        browser.close()
(ROOT / "PRESENTATION_BLACKBOX_REPORT.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(results,ensure_ascii=False))
