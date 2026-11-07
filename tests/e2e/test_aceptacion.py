"""Prueba de aceptación (E2E): simula a un usuario real en el navegador.

Flujo:
    1. Inicia la aplicación (fixture `url_app`).
    2. Abre un navegador y navega a la página principal.
    3. Encuentra el campo de texto del nuevo hábito y el botón "Agregar".
    4. Escribe "Tomar agua" y hace clic en el botón.
    5. Verifica que "Tomar agua" aparece en la página.
    6. Hace clic en "Marcar hoy" y verifica que la racha sube a 1.
"""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_usuario_agrega_y_marca_un_habito(page: Page, url_app: str):
    # Paso 2: abrir la página principal
    page.goto(url_app)
    expect(page.get_by_role("heading", name="Contador de Hábitos")).to_be_visible()

    # Pasos 3 y 4: escribir el hábito y pulsar "Agregar"
    page.get_by_placeholder("Ej: Tomar 2 litros de agua").fill("Tomar agua")
    page.get_by_role("button", name="Agregar").click()

    # Paso 5: el hábito aparece en la lista
    habito = page.locator("#lista-habitos li", has_text="Tomar agua")
    expect(habito).to_be_visible()
    expect(habito).to_contain_text("Racha: 0")

    # Paso 6: marcarlo como hecho hoy y verificar la racha
    habito.get_by_role("button", name="Marcar hoy").click()
    expect(habito).to_contain_text("Racha: 1")
    expect(habito.get_by_role("button", name="✓ Hecho hoy")).to_be_disabled()
