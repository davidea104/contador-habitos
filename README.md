# 🎯 Contador de Hábitos

Aplicación web para registrar hábitos diarios y llevar la **racha** de días consecutivos.
Desarrollada para la *Actividad en Clase de Integración Continua* (EAFIT).

- **Backend:** Python + FastAPI (`app/`)
- **Frontend:** HTML + JavaScript (`static/index.html`)
- **Base de datos (opcional):** PostgreSQL (`docker-compose.yml`); sin ella guarda en memoria
- **Pruebas unitarias:** pytest (`tests/unit/`)
- **Cobertura:** pytest-cov / coverage.py (`.coveragerc`)
- **Prueba de aceptación (E2E):** Playwright + pytest (`tests/e2e/`)

---

## 1. Diseño y desarrollo de la aplicación

### Arquitectura

```
Navegador (static/index.html)
        │  fetch() JSON
        ▼
API REST  (app/main.py)        ← capa HTTP: valida la entrada y traduce errores a códigos HTTP
        │
        ▼
Lógica    (app/habitos.py)     ← reglas de negocio puras (sin HTTP), fáciles de probar de forma aislada
        │
        ▼
Repositorio (app/repositorios.py)
        ├── RepositorioPostgres  ← si DATABASE_URL existe y PostgreSQL responde
        └── RepositorioMemoria   ← respaldo automático si no hay base de datos
```

La lógica se separó del framework para que las pruebas unitarias no dependan de HTTP.
El "reloj" y el repositorio se **inyectan** (`ContadorHabitos(reloj=..., repositorio=...)`),
así las pruebas pueden simular días distintos y elegir dónde se guardan los datos.

### Base de datos opcional (con respaldo en memoria)

Al arrancar, `crear_repositorio()` decide dónde guardar:

| Situación                                         | Almacenamiento | Log al arrancar                          |
|---------------------------------------------------|----------------|------------------------------------------|
| `DATABASE_URL` no definida                        | memoria        | `INFO: DATABASE_URL no definida…`        |
| `DATABASE_URL` definida pero la BD no responde    | memoria        | `WARNING: No se pudo conectar…`          |
| `DATABASE_URL` definida y la BD responde          | PostgreSQL     | `INFO: Conectado a PostgreSQL`           |

La interfaz muestra una etiqueta con el almacenamiento en uso (también en `GET /api/estado`).
Las tablas se crean solas la primera vez. La decisión se toma **al arrancar**: si la BD se
cae después, hay que reiniciar la app.

Para usar PostgreSQL en local (requiere Docker):

```bash
docker compose up -d --wait
export DATABASE_URL=postgresql://habitos:habitos@localhost:5433/habitos
uvicorn app.main:app --reload
```

El contenedor usa el puerto **5433** para no chocar con un PostgreSQL instalado en el equipo.

### Endpoints

| Método   | Ruta                          | Función           | Respuestas          |
|----------|-------------------------------|-------------------|---------------------|
| `GET`    | `/`                           | Interfaz HTML     | 200                 |
| `GET`    | `/api/habitos`                | `listar_habitos`  | 200                 |
| `POST`   | `/api/habitos`                | `agregar_habito`  | 201, 400, 422       |
| `POST`   | `/api/habitos/{id}/marcar`    | `marcar_habito`   | 200, 404, 409       |
| `DELETE` | `/api/habitos/{id}`           | `eliminar_habito` | 204, 404            |
| `GET`    | `/api/estado`                 | almacenamiento    | 200                 |

Documentación interactiva (Swagger): http://127.0.0.1:8000/docs

### Reglas de negocio

- El nombre no puede estar vacío ni superar 50 caracteres.
- No se permiten hábitos duplicados (sin distinguir mayúsculas).
- Un hábito solo se puede marcar **una vez por día**.
- **Racha** = días consecutivos completados. Si hoy aún no se ha marcado pero ayer sí, la racha
  sigue viva; si se salta un día completo, la racha vuelve a 0.

### Instalación y ejecución

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium        # solo para la prueba E2E
uvicorn app.main:app --reload
```

Abrir http://127.0.0.1:8000

> Sin `DATABASE_URL` los datos se guardan en memoria y se pierden al reiniciar el servidor.

### Ejecutar en GitHub Codespaces

En GitHub: **Code → Codespaces → Create codespace on main**. El archivo `.devcontainer/devcontainer.json`
instala las dependencias y Chromium automáticamente. Luego, en la terminal del Codespace:

```bash
uvicorn app.main:app --reload --host 0.0.0.0
```

El puerto 8000 se reenvía solo y se abre en el navegador. Las pruebas aparecen en el panel
**Testing** de VS Code (configurado en `.vscode/settings.json`).

---

## 2. Pruebas unitarias y cobertura

### Pruebas unitarias

- `tests/unit/test_habitos.py`: prueba la lógica (`agregar_habito`, `listar_habitos`,
  `obtener_habito`, `marcar_habito`, `eliminar_habito`, `calcular_racha`) de forma
  **aislada**. Por ejemplo, después de `agregar_habito` se verifica que la lista interna realmente
  contiene el nuevo hábito.
- `tests/unit/test_repositorios.py`: pruebas de **contrato** que corren contra los dos
  repositorios (memoria y PostgreSQL) y pruebas del respaldo en memoria cuando la BD no existe.
  La variante PostgreSQL solo corre si se define `TEST_DATABASE_URL`; si no, se omite (*skip*):
  ```bash
  TEST_DATABASE_URL=postgresql://habitos:habitos@localhost:5433/habitos pytest tests/unit --cov
  ```
- `tests/unit/test_api.py`: prueba cada endpoint con el `TestClient` de FastAPI. Cada prueba
  inyecta un `ContadorHabitos` nuevo con `app.dependency_overrides`, así no comparten estado.

Todas siguen la estrategia **AAA (Arrange, Act, Assert)**.

### ¿Cómo se mide la cobertura en Python? (investigación)

Python usa **coverage.py**, que registra qué líneas (y ramas) se ejecutan mientras corren las
pruebas. El plugin **pytest-cov** lo integra con pytest mediante la opción `--cov`.
La configuración está en `.coveragerc`:

- `source = app`: mide solo el código de la aplicación, no las pruebas.
- `branch = True`: además de líneas, mide **ramas** (que cada `if` se haya evaluado como verdadero *y*
  como falso).

### Generar el reporte

```bash
pytest tests/unit --cov --cov-report=term-missing --cov-report=html
open htmlcov/index.html            # reporte navegable línea por línea
```

### Análisis del reporte

**Sin base de datos** (50 pruebas pasan, 8 se omiten):

```
Name                  Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------
app/habitos.py           57      0     16      0   100%
app/main.py              44      0      0      0   100%
app/modelos.py            5      0      0      0   100%
app/repositorios.py      73     21      6      0    68%   85, 91-101, 104, ...
-----------------------------------------------------------------
TOTAL                   179     21     22      0    88%
```

**Con PostgreSQL** (`TEST_DATABASE_URL` definida, 58 pruebas pasan): **100 %** en todos los archivos.

- **¿Qué porcentaje está cubierto?** El 88 % sin base de datos y el 100 % con PostgreSQL, incluidas
  las 22 ramas.
- **¿Hay líneas o ramas sin probar?** Sin base de datos, sí: las líneas que faltan son
  exactamente los métodos de `RepositorioPostgres`, porque sus pruebas se omiten. El reporte sirve
  para ver que la parte sin probar es solo el acceso a la base de datos, no la lógica de negocio.
  Por eso CI tiene un job aparte con PostgreSQL. Las ramas más importantes de la lógica son las de
  `calcular_racha` (marcado hoy / marcado ayer / racha rota / hueco en medio) y las validaciones
  de `agregar_habito` (vacío, demasiado largo, duplicado). Cada una tiene una prueba dedicada.
- **Ojo:** 100 % de cobertura **no** significa que no haya errores. Solo indica que cada línea se
  ejecutó al menos una vez. La calidad depende de que los `assert` verifiquen el comportamiento
  correcto. Por ejemplo, la cobertura no detectaría un error de zona horaria, porque el reloj está
  simulado.

> Experimento sugerido: comenta la prueba `test_calcular_racha_sigue_viva_si_se_marco_ayer_pero_no_hoy`
> y vuelve a correr el reporte. En la columna `Missing` aparecerán las líneas o ramas de
> `calcular_racha` que dejaron de probarse.

---

## 3. Prueba de aceptación (E2E)

### ¿Cómo automatizar los clics de un usuario? (investigación)

Herramientas como **Selenium** o **Playwright** controlan un navegador real. Se eligió
**Playwright** con su plugin `pytest-playwright` porque:

- Entrega una fixture `page` lista para usar en pytest.
- Espera automáticamente a que los elementos aparezcan (`expect(...)`), sin `sleep` manuales.
- Permite buscar elementos como lo haría un usuario (`get_by_role`, `get_by_placeholder`).

### Flujo implementado (`tests/e2e/test_aceptacion.py`)

1. La fixture `url_app` (`tests/e2e/conftest.py`) **inicia la aplicación** con uvicorn en un puerto libre.
2. Abre el navegador y navega a la página principal (localhost).
3. Encuentra el campo de texto y el botón **"Agregar"**.
4. Escribe **"Tomar agua"** y hace clic.
5. **Assert:** "Tomar agua" aparece en la página con `Racha: 0`.
6. Hace clic en **"Marcar hoy"** y verifica `Racha: 1` y el botón "✓ Hecho hoy" deshabilitado.

### Ejecutar

```bash
pytest tests/e2e                   # navegador oculto (headless)
pytest tests/e2e --headed --slowmo 500   # para ver el navegador en acción
```

### Ejecutar todas las pruebas

```bash
pytest --cov --cov-report=term-missing
```

---

## 4. Integración continua (GitHub Actions)

El pipeline `.github/workflows/ci.yml` se ejecuta en cada push a `main`, en cada pull request y de
forma manual (`workflow_dispatch`). Tiene tres jobs:

1. **Pruebas unitarias y cobertura:** corre `pytest tests/unit --cov`, publica la tabla de cobertura
   en el resumen del run y guarda el reporte HTML como *artifact* (`reporte-cobertura`).
   El job **falla si la cobertura baja del 85 %** (`fail_under` en `.coveragerc`); sin base de datos
   el código de PostgreSQL no se ejecuta y la cobertura queda en ≈ 88 %.
2. **Integración con PostgreSQL (opcional):** levanta PostgreSQL como *service container*, corre
   las mismas pruebas con `TEST_DATABASE_URL` y exige ≥ 95 % de cobertura. Tiene
   `continue-on-error: true`: si la base de datos da problemas, **el pipeline no se bloquea**.
3. **Prueba de aceptación (E2E):** solo corre si el job de pruebas unitarias pasó (`needs`). Instala Chromium
   y ejecuta la prueba con Playwright. Si falla, guarda las trazas (`trazas-playwright`), que se
   pueden abrir con `playwright show-trace`.

Los resultados se ven en la pestaña **Actions** del repositorio en GitHub.
