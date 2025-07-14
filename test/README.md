# Tests para TCS Downloader

Este directorio contiene tests completos para la clase `TCSDownloader` usando pytest.

## Estructura

```
test/
├── README.md               # Este archivo
├── __init__.py             # Paquete de tests
├── test_tcs_downloader.py  # Test suite principal
├── create_test_files.py    # Script para crear archivos de prueba
└── fixtures/               # Archivos de prueba
    ├── __init__.py
    ├── pliego_bases_condiciones.docx
    ├── carta_invitacion.docx
    ├── pbc_licitacion.docx
    ├── documento_general.docx
    ├── pliego_bases_condiciones.doc
    ├── documentos_pbc.zip
    ├── documentos_carta.zip
    ├── documentos_sin_pbc.zip
    ├── documentos_pbc.rar
    └── pliego_bases_condiciones.pdf
```

## Requisitos

### Dependencias Python
```bash
pip install pytest pytest-mock python-docx pypandoc rarfile
```

### Herramientas del Sistema
- **Pandoc**: Para conversión de documentos
- **BasicTeX**: Para motor PDF (pdflatex)
- **unar**: Para extracción de archivos RAR

#### Instalación en macOS
```bash
# Instalar herramientas necesarias
brew install pandoc
brew install --cask basictex
brew install unar

# Actualizar PATH para incluir LaTeX
eval "$(/usr/libexec/path_helper)"
```

## Ejecución de Tests

### Ejecutar todos los tests
```bash
pytest test/test_tcs_downloader.py -v
```

### Ejecutar tests específicos
```bash
# Solo tests de API
pytest test/test_tcs_downloader.py::TestTCSDownloader::test_get_document_list_success -v

# Solo tests de validación
pytest test/test_tcs_downloader.py -k "is_valid_document" -v

# Solo tests de extracción
pytest test/test_tcs_downloader.py -k "extract_pbc" -v

# Solo tests de conversión
pytest test/test_tcs_downloader.py -k "convert_docx_to_pdf" -v
```

### Ejecutar tests con cobertura
```bash
pip install pytest-cov
pytest test/test_tcs_downloader.py --cov=src/modules/tcs_downloader --cov-report=html
```

## Funciones Testadas

### ✅ Funciones de API
- `get_document_list()` - Obtener lista de documentos desde API
- `select_document()` - Seleccionar documento PBC/carta

### ✅ Funciones de Validación
- `is_valid_document()` - Validar documento por nombre
- `check_document_mime_type()` - Obtener tipo MIME

### ✅ Funciones de Descarga
- `download_document_tmp()` - Descargar a archivo temporal

### ✅ Funciones de Extracción
- `extract_pbc_from_zip()` - Extraer PBC de archivo ZIP
- `extract_pbc_from_rar()` - Extraer PBC de archivo RAR

### ✅ Funciones de Conversión
- `convert_docx_to_pdf()` - Convertir DOCX a PDF

## Tipos de Tests

### Tests Unitarios
- Pruebas individuales de cada función
- Mocks para llamadas HTTP
- Validación de parámetros y retornos

### Tests de Integración
- Flujo completo ZIP → DOCX → PDF
- Validación de archivos reales
- Interacción entre múltiples funciones

### Tests de Casos Edge
- Archivos no encontrados
- Formatos inválidos
- Errores de red
- Archivos corruptos

## Archivos de Prueba

Los archivos de prueba se crean automáticamente con:
```bash
cd test
python create_test_files.py
```

### Archivos DOCX
- `pliego_bases_condiciones.docx` - PBC válido
- `carta_invitacion.docx` - Carta válida
- `pbc_licitacion.docx` - PBC alternativo
- `documento_general.docx` - Documento inválido

### Archivos ZIP
- `documentos_pbc.zip` - ZIP con PBC válido
- `documentos_carta.zip` - ZIP con carta válida
- `documentos_sin_pbc.zip` - ZIP sin documentos válidos

### Archivos RAR
- `documentos_pbc.rar` - RAR con PBC válido

## Configuración

### pytest.ini
```ini
[tool:pytest]
testpaths = test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers --disable-warnings
```

### Fixtures
- `downloader` - Instancia de TCSDownloader
- `fixtures_dir` - Directorio de archivos de prueba
- `mock_api_response` - Respuesta mock de API

## Solución de Problemas

### Error "pdflatex not found"
```bash
# Instalar BasicTeX
brew install --cask basictex

# Actualizar PATH
eval "$(/usr/libexec/path_helper)"

# Verificar instalación
which pdflatex
```

### Error "rar command not found"
```bash
# Instalar unar
brew install unar

# Verificar instalación
which unar
```

### Error "pandoc not found"
```bash
# Instalar pandoc
brew install pandoc

# Verificar instalación
pandoc --version
```

## Resultados

✅ **34 tests pasando**
- 10 tests de API y selección
- 8 tests de validación
- 2 tests de descarga
- 5 tests de extracción ZIP
- 2 tests de extracción RAR
- 3 tests de conversión PDF
- 4 tests de integración

⏱️ **Tiempo de ejecución**: ~2 segundos

📊 **Cobertura**: 100% de las funciones principales 