import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.getenv("INVISAP_TEST_URL", "http://127.0.0.1:5600")
RESULTS_DIR = Path(__file__).resolve().parents[1] / "test-results"


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            response = page.goto(f"{BASE_URL}/login", wait_until="networkidle")
            page.locator("#loader-out").wait_for(state="hidden", timeout=10000)
            forms = page.locator("form").count()
            inputs = page.locator("input").count()
            if response is None or response.status != 200:
                raise RuntimeError(
                    f"GET /login devolvió HTTP {response.status if response else 'sin respuesta'}"
                )
            if forms == 0 or inputs < 2:
                raise AssertionError(
                    f"Formulario de acceso incompleto: forms={forms}, inputs={inputs}"
                )
            if page.get_by_text("Primero debes iniciar sesión.", exact=True).count():
                raise AssertionError("La página de acceso mostró un aviso de sesión incorrecto.")
            screenshot = RESULTS_DIR / "playwright_login.png"
            page.screenshot(path=str(screenshot), full_page=True)
            print(
                f"UI aprobada: HTTP {response.status}; "
                f"título={page.title()!r}; formularios={forms}; campos={inputs}"
            )
            print(f"Captura: {screenshot}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
