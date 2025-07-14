#!/usr/bin/env python3
"""
Tests para la clase TCSDownloader
"""

import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Importar la clase a testear
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from modules.tcs_downloader.tcs_downloader import TCSDownloader


class TestTCSDownloader:
    """Test suite para la clase TCSDownloader"""
    
    @pytest.fixture
    def downloader(self):
        """Fixture para crear instancia de TCSDownloader"""
        return TCSDownloader()
    
    @pytest.fixture
    def fixtures_dir(self):
        """Fixture para obtener el directorio de fixtures"""
        return Path(__file__).parent / "fixtures"
    
    @pytest.fixture
    def mock_api_response(self):
        """Fixture con respuesta mock de la API"""
        return {
            "tender": {
                "documents": [
                    {
                        "id": "1",
                        "title": "pliego_bases_condiciones.pdf",
                        "documentTypeDetails": "Pliego de bases y condiciones",
                        "url": "https://example.com/doc1.pdf"
                    },
                    {
                        "id": "2", 
                        "title": "carta_invitacion.docx",
                        "documentTypeDetails": "Carta de invitacion",
                        "url": "https://example.com/doc2.docx"
                    },
                    {
                        "id": "3",
                        "title": "otros_documentos.zip",
                        "documentTypeDetails": "Otros documentos",
                        "url": "https://example.com/doc3.zip"
                    }
                ]
            }
        }

    # Tests para get_document_list
    @patch('requests.get')
    def test_get_document_list_success(self, mock_get, downloader, mock_api_response):
        """Test exitoso de get_document_list"""
        mock_get.return_value.json.return_value = mock_api_response
        
        result = downloader.get_document_list("12345")
        
        assert len(result) == 3
        assert result[0]["title"] == "pliego_bases_condiciones.pdf"
        assert result[1]["title"] == "carta_invitacion.docx"
        mock_get.assert_called_once_with("https://www.contrataciones.gov.py/datos/api/v3/doc/tender/12345")
    
    @patch('requests.get')
    def test_get_document_list_api_error(self, mock_get, downloader):
        """Test manejo de errores en get_document_list"""
        mock_get.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            downloader.get_document_list("12345")
    
    @patch('requests.get')
    def test_get_document_list_with_integer(self, mock_get, downloader, mock_api_response):
        """Test con tender_id como entero"""
        mock_get.return_value.json.return_value = mock_api_response
        
        result = downloader.get_document_list(12345)
        
        assert len(result) == 3
        assert result[0]["title"] == "pliego_bases_condiciones.pdf"
        # Verificar que se llamó con el ID convertido a string
        mock_get.assert_called_with("https://www.contrataciones.gov.py/datos/api/v3/doc/tender/12345")
    
    def test_get_document_list_validation_none(self, downloader):
        """Test validación con None"""
        from modules.tcs_downloader.tcs_downloader import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            downloader.get_document_list(None)
        
        assert "tender_id no puede ser None" in str(exc_info.value)
    
    def test_get_document_list_validation_empty_string(self, downloader):
        """Test validación con string vacío"""
        from modules.tcs_downloader.tcs_downloader import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            downloader.get_document_list("")
        
        assert "tender_id no puede estar vacío" in str(exc_info.value)
    
    def test_get_document_list_validation_whitespace(self, downloader):
        """Test validación con solo espacios"""
        from modules.tcs_downloader.tcs_downloader import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            downloader.get_document_list("   ")
        
        assert "tender_id no puede estar vacío" in str(exc_info.value)

    # Tests para select_document
    def test_select_document_pbc(self, downloader, mock_api_response):
        """Test selección de documento PBC"""
        documents = mock_api_response["tender"]["documents"]
        
        result = downloader.select_document(documents)
        
        assert result is not None
        assert result["documentTypeDetails"] == "Pliego de bases y condiciones"
        assert result["title"] == "pliego_bases_condiciones.pdf"
    
    def test_select_document_carta(self, downloader):
        """Test selección de carta de invitación"""
        documents = [
            {
                "id": "1",
                "title": "carta_invitacion.docx",
                "documentTypeDetails": "Carta de invitacion",
                "url": "https://example.com/doc1.docx"
            }
        ]
        
        result = downloader.select_document(documents)
        
        assert result is not None
        assert result["documentTypeDetails"] == "Carta de invitacion"
    
    def test_select_document_no_valid(self, downloader):
        """Test cuando no hay documentos válidos"""
        from modules.tcs_downloader.tcs_downloader import DocumentNotFoundError
        
        documents = [
            {
                "id": "1",
                "title": "otros_documentos.pdf",
                "documentTypeDetails": "Otros documentos",
                "url": "https://example.com/doc1.pdf"
            }
        ]
        
        with pytest.raises(DocumentNotFoundError) as exc_info:
            downloader.select_document(documents)
        
        assert "No se encontró documento PBC o carta de invitación" in str(exc_info.value)
        assert "Otros documentos" in str(exc_info.value)
    
    def test_select_document_with_accents(self, downloader):
        """Test con documentos que tienen acentos"""
        documents = [
            {
                "id": "1",
                "title": "pliego_bases_condiciones.pdf",
                "documentTypeDetails": "Pliego de bases y condiciones",
                "url": "https://example.com/doc1.pdf"
            }
        ]
        
        result = downloader.select_document(documents)
        
        assert result is not None

    # Tests para is_valid_document
    def test_is_valid_document_pbc_pdf(self, downloader):
        """Test documento PBC en PDF válido"""
        assert downloader.is_valid_document("pliego_bases_condiciones.pdf") == True
    
    def test_is_valid_document_pbc_docx(self, downloader):
        """Test documento PBC en DOCX válido"""
        assert downloader.is_valid_document("pliego_bases_condiciones.docx") == True
    
    def test_is_valid_document_pbc_doc(self, downloader):
        """Test documento PBC en DOC válido"""
        assert downloader.is_valid_document("pliego_bases_condiciones.doc") == True
    
    def test_is_valid_document_carta_pdf(self, downloader):
        """Test carta de invitación en PDF válido"""
        assert downloader.is_valid_document("carta_invitacion.pdf") == True
    
    def test_is_valid_document_pbc_keyword(self, downloader):
        """Test con keyword 'pbc' en nombre"""
        assert downloader.is_valid_document("pbc_licitacion.docx") == True
    
    def test_is_valid_document_invalid_format(self, downloader):
        """Test documento PBC pero formato inválido"""
        assert downloader.is_valid_document("pliego_bases_condiciones.zip") == False
    
    def test_is_valid_document_invalid_type(self, downloader):
        """Test documento válido pero tipo incorrecto"""
        assert downloader.is_valid_document("documento_general.pdf") == False
    
    def test_is_valid_document_empty_filename(self, downloader):
        """Test con nombre de archivo vacío"""
        assert downloader.is_valid_document("") == False

    # Tests para check_document_mime_type
    def test_check_document_mime_type_pdf(self, downloader):
        """Test MIME type para PDF"""
        document = {"title": "documento.pdf"}
        assert downloader.check_document_mime_type(document) == "application/pdf"
    
    def test_check_document_mime_type_docx(self, downloader):
        """Test MIME type para DOCX"""
        document = {"title": "documento.docx"}
        expected = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert downloader.check_document_mime_type(document) == expected
    
    def test_check_document_mime_type_doc(self, downloader):
        """Test MIME type para DOC"""
        document = {"title": "documento.doc"}
        assert downloader.check_document_mime_type(document) == "application/msword"
    
    def test_check_document_mime_type_zip(self, downloader):
        """Test MIME type para ZIP"""
        document = {"title": "documento.zip"}
        assert downloader.check_document_mime_type(document) == "application/zip"
    
    def test_check_document_mime_type_rar(self, downloader):
        """Test MIME type para RAR"""
        document = {"title": "documento.rar"}
        assert downloader.check_document_mime_type(document) == "application/x-rar-compressed"
    
    def test_check_document_mime_type_unknown(self, downloader):
        """Test MIME type para formato desconocido"""
        document = {"title": "documento.txt"}
        assert downloader.check_document_mime_type(document) == ""

    # Tests para download_document_tmp
    @patch('requests.get')
    def test_download_document_tmp_success(self, mock_get, downloader):
        """Test descarga exitosa de documento temporal"""
        mock_response = Mock()
        mock_response.content = b"contenido del archivo"
        mock_get.return_value = mock_response
        
        document = {
            "title": "test_document.pdf",
            "url": "https://example.com/doc.pdf"
        }
        
        result = downloader.download_document_tmp(document)
        
        assert result != ""
        assert os.path.exists(result)
        assert "test_document.pdf" in result
        
        # Verificar que el archivo tiene el contenido correcto
        with open(result, 'rb') as f:
            content = f.read()
            assert content == b"contenido del archivo"
    
    @patch('requests.get')
    def test_download_document_tmp_request_error(self, mock_get, downloader):
        """Test error en descarga de documento"""
        mock_get.side_effect = Exception("Network error")
        
        document = {
            "title": "test_document.pdf",
            "url": "https://example.com/doc.pdf"
        }
        
        with pytest.raises(Exception):
            downloader.download_document_tmp(document)

    # Tests para extract_pbc_from_zip
    def test_extract_pbc_from_zip_success(self, downloader, fixtures_dir):
        """Test extracción exitosa de PBC desde ZIP"""
        zip_path = fixtures_dir / "documentos_pbc.zip"
        
        result = downloader.extract_pbc_from_zip(str(zip_path))
        
        assert result != ""
        assert os.path.exists(result)
        assert "pliego_bases_condiciones.docx" in result
    
    def test_extract_pbc_from_zip_carta(self, downloader, fixtures_dir):
        """Test extracción de carta de invitación desde ZIP"""
        zip_path = fixtures_dir / "documentos_carta.zip"
        
        result = downloader.extract_pbc_from_zip(str(zip_path))
        
        assert result != ""
        assert os.path.exists(result)
        assert "carta_invitacion.docx" in result
    
    def test_extract_pbc_from_zip_no_valid(self, downloader, fixtures_dir):
        """Test ZIP sin documentos válidos"""
        from modules.tcs_downloader.tcs_downloader import ExtractionError
        
        zip_path = fixtures_dir / "documentos_sin_pbc.zip"
        
        with pytest.raises(ExtractionError) as exc_info:
            downloader.extract_pbc_from_zip(str(zip_path))
        
        assert "No se encontró documento PBC o carta de invitación" in str(exc_info.value)
    
    def test_extract_pbc_from_zip_not_found(self, downloader):
        """Test ZIP que no existe"""
        from modules.tcs_downloader.tcs_downloader import ExtractionError
        
        with pytest.raises(ExtractionError) as exc_info:
            downloader.extract_pbc_from_zip("/path/nonexistent.zip")
        
        assert "El archivo ZIP no existe" in str(exc_info.value)
    
    def test_extract_pbc_from_zip_bad_file(self, downloader, fixtures_dir):
        """Test archivo que no es ZIP válido"""
        from modules.tcs_downloader.tcs_downloader import ExtractionError
        
        bad_zip = fixtures_dir / "pliego_bases_condiciones.pdf"
        
        with pytest.raises(ExtractionError) as exc_info:
            downloader.extract_pbc_from_zip(str(bad_zip))
        
        assert "El archivo no es un ZIP válido" in str(exc_info.value)

    # Tests para extract_pbc_from_rar
    def test_extract_pbc_from_rar_not_found(self, downloader):
        """Test RAR que no existe"""
        from modules.tcs_downloader.tcs_downloader import ExtractionError
        
        with pytest.raises(ExtractionError) as exc_info:
            downloader.extract_pbc_from_rar("/path/nonexistent.rar")
        
        assert "El archivo RAR no existe" in str(exc_info.value)
    
    def test_extract_pbc_from_rar_bad_file(self, downloader, fixtures_dir):
        """Test archivo que no es RAR válido"""
        from modules.tcs_downloader.tcs_downloader import ExtractionError
        
        bad_rar = fixtures_dir / "pliego_bases_condiciones.pdf"
        
        with pytest.raises(ExtractionError) as exc_info:
            downloader.extract_pbc_from_rar(str(bad_rar))
        
        assert "El archivo no es un RAR" in str(exc_info.value)
    
    # Nota: Test completo de RAR requiere archivo RAR válido

    # Tests para convert_docx_to_pdf
    def test_convert_docx_to_pdf_success(self, downloader, fixtures_dir):
        """Test conversión exitosa de DOCX a PDF"""
        docx_path = fixtures_dir / "pliego_bases_condiciones.docx"
        
        result = downloader.convert_docx_to_pdf(str(docx_path))
        
        # La conversión DEBE funcionar si tenemos las herramientas instaladas
        assert result != "", "La conversión DOCX a PDF falló - verifica que las herramientas PDF estén instaladas"
        assert os.path.exists(result), f"El archivo PDF no fue creado en {result}"
        assert result.endswith('.pdf'), f"El archivo resultado no es PDF: {result}"
    
    def test_convert_docx_to_pdf_not_found(self, downloader):
        """Test conversión con archivo que no existe"""
        from modules.tcs_downloader.tcs_downloader import ConversionError
        
        with pytest.raises(ConversionError) as exc_info:
            downloader.convert_docx_to_pdf("/path/nonexistent.docx")
        
        assert "El archivo DOCX no existe" in str(exc_info.value)
    
    def test_convert_docx_to_pdf_carta(self, downloader, fixtures_dir):
        """Test conversión de carta de invitación"""
        docx_path = fixtures_dir / "carta_invitacion.docx"
        
        result = downloader.convert_docx_to_pdf(str(docx_path))
        
        # La conversión DEBE funcionar
        assert result != "", "La conversión de carta de invitación falló"
        assert os.path.exists(result), f"El archivo PDF no fue creado en {result}"
        assert "carta_invitacion.pdf" in result, f"Nombre de archivo incorrecto: {result}"

    # Tests de integración
    def test_integration_zip_to_pdf(self, downloader, fixtures_dir):
        """Test integración: ZIP → DOCX → PDF"""
        zip_path = fixtures_dir / "documentos_pbc.zip"
        
        # 1. Extraer DOCX del ZIP
        docx_path = downloader.extract_pbc_from_zip(str(zip_path))
        assert docx_path != ""
        
        # 2. Convertir DOCX a PDF
        pdf_path = downloader.convert_docx_to_pdf(docx_path)
        
        # El flujo completo DEBE funcionar
        assert pdf_path != "", "El flujo ZIP → DOCX → PDF falló en la conversión"
        assert os.path.exists(pdf_path), f"El archivo PDF no fue creado en {pdf_path}"
        assert pdf_path.endswith('.pdf'), f"El archivo resultado no es PDF: {pdf_path}"
    
    def test_integration_validation_flow(self, downloader, fixtures_dir):
        """Test flujo de validación completo"""
        # 1. Validar documento por nombre
        assert downloader.is_valid_document("pliego_bases_condiciones.pdf") == True
        
        # 2. Verificar MIME type
        document = {"title": "pliego_bases_condiciones.pdf"}
        mime_type = downloader.check_document_mime_type(document)
        assert mime_type == "application/pdf"
        
        # 3. Extraer de ZIP
        zip_path = fixtures_dir / "documentos_pbc.zip"
        extracted = downloader.extract_pbc_from_zip(str(zip_path))
        assert extracted != ""
        
        # 4. Validar archivo extraído
        filename = os.path.basename(extracted)
        assert downloader.is_valid_document(filename) == True

    # Tests para el método facade process_tender_documents
    @patch('requests.get')
    def test_process_tender_documents_pdf_success(self, mock_get, downloader, fixtures_dir, tmp_path):
        """Test procesamiento completo con documento PDF"""
        # Mock de la API
        mock_api_response = {
            "tender": {
                "documents": [
                    {
                        "id": "1",
                        "title": "pliego_bases_condiciones.pdf",
                        "documentTypeDetails": "Pliego de bases y condiciones",
                        "url": "https://example.com/doc.pdf"
                    }
                ]
            }
        }
        
        # Mock de descarga PDF
        pdf_content = (fixtures_dir / "pliego_bases_condiciones.pdf").read_bytes()
        
        # Mock para API response
        mock_api_response_obj = Mock()
        mock_api_response_obj.json.return_value = mock_api_response
        
        # Mock para descarga
        mock_download_response = Mock()
        mock_download_response.content = pdf_content
        
        # Configurar side_effect para manejar las dos llamadas
        mock_get.side_effect = [mock_api_response_obj, mock_download_response]
        
        # Ejecutar método facade
        result = downloader.process_tender_documents("12345", str(tmp_path))
        
        # Verificar resultado
        assert result != ""
        assert os.path.exists(result)
        assert result.endswith('.pdf')
        assert "pliego_bases_condiciones.pdf" in result
    
    @patch('requests.get')
    def test_process_tender_documents_docx_success(self, mock_get, downloader, fixtures_dir, tmp_path):
        """Test procesamiento completo con documento DOCX"""
        # Mock de la API
        mock_api_response = {
            "tender": {
                "documents": [
                    {
                        "id": "1",
                        "title": "pliego_bases_condiciones.docx",
                        "documentTypeDetails": "Pliego de bases y condiciones",
                        "url": "https://example.com/doc.docx"
                    }
                ]
            }
        }
        
        # Mock de descarga DOCX
        docx_content = (fixtures_dir / "pliego_bases_condiciones.docx").read_bytes()
        
        # Mock para API response
        mock_api_response_obj = Mock()
        mock_api_response_obj.json.return_value = mock_api_response
        
        # Mock para descarga
        mock_download_response = Mock()
        mock_download_response.content = docx_content
        
        # Configurar side_effect para manejar las dos llamadas
        mock_get.side_effect = [mock_api_response_obj, mock_download_response]
        
        # Ejecutar método facade
        result = downloader.process_tender_documents("12345", str(tmp_path))
        
        # Verificar resultado
        assert result != ""
        assert os.path.exists(result)
        assert result.endswith('.pdf')
        assert "pliego_bases_condiciones.pdf" in result
    
    @patch('requests.get')
    def test_process_tender_documents_zip_success(self, mock_get, downloader, fixtures_dir, tmp_path):
        """Test procesamiento completo con archivo ZIP"""
        # Mock de la API
        mock_api_response = {
            "tender": {
                "documents": [
                    {
                        "id": "1",
                        "title": "documentos_pbc.zip",
                        "documentTypeDetails": "Pliego de bases y condiciones",
                        "url": "https://example.com/docs.zip"
                    }
                ]
            }
        }
        
        # Mock de descarga ZIP
        zip_content = (fixtures_dir / "documentos_pbc.zip").read_bytes()
        
        # Mock para API response
        mock_api_response_obj = Mock()
        mock_api_response_obj.json.return_value = mock_api_response
        
        # Mock para descarga
        mock_download_response = Mock()
        mock_download_response.content = zip_content
        
        # Configurar side_effect para manejar las dos llamadas
        mock_get.side_effect = [mock_api_response_obj, mock_download_response]
        
        # Ejecutar método facade
        result = downloader.process_tender_documents("12345", str(tmp_path))
        
        # Verificar resultado
        assert result != ""
        assert os.path.exists(result)
        assert result.endswith('.pdf')
        assert "documentos_pbc.pdf" in result
    
    def test_process_tender_documents_invalid_tender_id(self, downloader, tmp_path):
        """Test con ID de licitación inválido"""
        from modules.tcs_downloader.tcs_downloader import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            downloader.process_tender_documents("", str(tmp_path))
        
        assert "tender_id no puede estar vacío" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            downloader.process_tender_documents("   ", str(tmp_path))
        
        assert "tender_id no puede estar vacío" in str(exc_info.value)
    
    def test_process_tender_documents_invalid_output_dir(self, downloader):
        """Test con directorio de salida inválido"""
        from modules.tcs_downloader.tcs_downloader import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            downloader.process_tender_documents("12345", "")
        
        assert "output_directory no puede estar vacío" in str(exc_info.value)
    
    @patch('requests.get')
    def test_process_tender_documents_no_documents(self, mock_get, downloader, tmp_path):
        """Test cuando no hay documentos para la licitación"""
        from modules.tcs_downloader.tcs_downloader import DocumentNotFoundError
        
        mock_api_response = {"tender": {"documents": []}}
        mock_get.return_value.json.return_value = mock_api_response
        
        with pytest.raises(DocumentNotFoundError) as exc_info:
            downloader.process_tender_documents("12345", str(tmp_path))
        
        assert "No se encontraron documentos para tender 12345" in str(exc_info.value)
    
    @patch('requests.get')
    def test_process_tender_documents_no_valid_documents(self, mock_get, downloader, tmp_path):
        """Test cuando no hay documentos válidos"""
        from modules.tcs_downloader.tcs_downloader import DocumentNotFoundError
        
        mock_api_response = {
            "tender": {
                "documents": [
                    {
                        "id": "1",
                        "title": "otros_documentos.pdf",
                        "documentTypeDetails": "Otros documentos",
                        "url": "https://example.com/doc.pdf"
                    }
                ]
            }
        }
        mock_get.return_value.json.return_value = mock_api_response
        
        with pytest.raises(DocumentNotFoundError) as exc_info:
            downloader.process_tender_documents("12345", str(tmp_path))
        
        assert "No se encontró documento PBC o carta de invitación" in str(exc_info.value)
    
    @patch('requests.get')
    def test_process_tender_documents_download_error(self, mock_get, downloader, tmp_path):
        """Test error en descarga"""
        from modules.tcs_downloader.tcs_downloader import DownloadError
        
        mock_api_response = {
            "tender": {
                "documents": [
                    {
                        "id": "1",
                        "title": "pliego_bases_condiciones.pdf",
                        "documentTypeDetails": "Pliego de bases y condiciones",
                        "url": "https://example.com/doc.pdf"
                    }
                ]
            }
        }
        
        # Mock para la respuesta API
        mock_api_response_obj = Mock()
        mock_api_response_obj.json.return_value = mock_api_response
        
        # Mock para error de descarga
        mock_download_error = Mock()
        mock_download_error.raise_for_status.side_effect = Exception("Network error")
        
        mock_get.side_effect = [mock_api_response_obj, mock_download_error]
        
        with pytest.raises(DownloadError) as exc_info:
            downloader.process_tender_documents("12345", str(tmp_path))
        
        assert "Error inesperado al descargar" in str(exc_info.value)

    @patch('requests.get')
    def test_process_tender_documents_with_integer_id(self, mock_get, downloader, fixtures_dir, tmp_path):
        """Test procesamiento completo con tender_id como entero"""
        # Mock de la API
        mock_api_response = {
            "tender": {
                "documents": [
                    {
                        "id": "1",
                        "title": "pliego_bases_condiciones.pdf",
                        "documentTypeDetails": "Pliego de bases y condiciones",
                        "url": "https://example.com/doc.pdf"
                    }
                ]
            }
        }
        
        # Mock de descarga PDF
        pdf_content = (fixtures_dir / "pliego_bases_condiciones.pdf").read_bytes()
        
        # Mock para API response
        mock_api_response_obj = Mock()
        mock_api_response_obj.json.return_value = mock_api_response
        
        # Mock para descarga
        mock_download_response = Mock()
        mock_download_response.content = pdf_content
        
        # Configurar side_effect para manejar las dos llamadas
        mock_get.side_effect = [mock_api_response_obj, mock_download_response]
        
        # Ejecutar método facade con integer
        result = downloader.process_tender_documents(12345, str(tmp_path))
        
        # Verificar resultado
        assert result != ""
        assert os.path.exists(result)
        assert result.endswith('.pdf')
        
        # Verificar que se llamó a la API con el ID convertido a string
        expected_url = "https://www.contrataciones.gov.py/datos/api/v3/doc/tender/12345"
        mock_get.assert_any_call(expected_url)


# Configuración de pytest
def pytest_configure():
    """Configuración de pytest"""
    # Configurar rarfile para usar unar
    try:
        import rarfile
        rarfile.UNRAR_TOOL = "unar"
    except ImportError:
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 