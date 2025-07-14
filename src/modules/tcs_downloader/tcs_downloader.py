import requests
from unidecode import unidecode
import tempfile
import os
import zipfile
import rarfile
import pypandoc
import subprocess
import shutil
from pathlib import Path
from typing import Union

# Excepciones personalizadas
class TCSDownloaderError(Exception):
    """Excepción base para errores del TCS Downloader"""
    pass

class APIError(TCSDownloaderError):
    """Error al consultar la API de contrataciones"""
    pass

class DocumentNotFoundError(TCSDownloaderError):
    """No se encontró un documento válido"""
    pass

class DownloadError(TCSDownloaderError):
    """Error al descargar el documento"""
    pass

class ExtractionError(TCSDownloaderError):
    """Error al extraer archivo de ZIP/RAR"""
    pass

class ConversionError(TCSDownloaderError):
    """Error al convertir documento a PDF"""
    pass

class ValidationError(TCSDownloaderError):
    """Error de validación de parámetros"""
    pass

class TCSDownloader:

    def get_document_list(self, tender_id: Union[str, int]) -> list[object]:
        # Convertir a string y validar
        if tender_id is None:
            raise ValidationError("tender_id no puede ser None")
        
        tender_id_str = str(tender_id).strip()
        if not tender_id_str:
            raise ValidationError("tender_id no puede estar vacío")
        
        try:
            response = requests.get(f"https://www.contrataciones.gov.py/datos/api/v3/doc/tender/{tender_id_str}")
            response.raise_for_status()
            data = response.json()
            
            if "tender" not in data or "documents" not in data["tender"]:
                raise APIError(f"Respuesta de API inválida para tender {tender_id_str}")
            
            documents = data["tender"]["documents"]
            if not documents:
                raise DocumentNotFoundError(f"No se encontraron documentos para tender {tender_id_str}")
            
            return documents
            
        except requests.exceptions.RequestException as e:
            raise APIError(f"Error al consultar API para tender {tender_id_str}: {e}")
        except ValueError as e:
            raise APIError(f"Error al parsear respuesta JSON para tender {tender_id_str}: {e}")
        except KeyError as e:
            raise APIError(f"Estructura de respuesta inesperada para tender {tender_id_str}: {e}")

    def select_document(self, document_list: list[object]) -> object:
        if not document_list:
            raise ValidationError("document_list no puede estar vacía")
        
        for document in document_list:
            try:
                document_type = unidecode(document["documentTypeDetails"]).lower()
                if document_type in ["pliego de bases y condiciones", "carta de invitacion"]:
                    return document
            except KeyError:
                continue  # Si el documento no tiene documentTypeDetails, continuar
        
        # Si llegamos aquí, no encontramos ningún documento válido
        doc_types = []
        for doc in document_list:
            try:
                doc_types.append(doc.get("documentTypeDetails", "Sin tipo"))
            except:
                doc_types.append("Error al leer")
        
        raise DocumentNotFoundError(
            f"No se encontró documento PBC o carta de invitación. "
            f"Tipos disponibles: {', '.join(doc_types)}"
        )

    def is_valid_document(self, filename: str) -> bool:
        """
        Verifica si un documento es una PBC o carta de invitación en formato PDF o DOC/DOCX.
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            bool: True si el documento es válido, False en caso contrario
        """
        # Verificar tipo de documento por el nombre del archivo
        filename_lower = unidecode(filename).lower()
        is_pbc_or_invitation = (
            "pliego" in filename_lower or 
            "pbc" in filename_lower or
            "carta" in filename_lower or
            "invitacion" in filename_lower
        )
        
        # Verificar formato por extensión
        is_valid_format = (
            filename.lower().endswith('.pdf') or
            filename.lower().endswith('.doc') or
            filename.lower().endswith('.docx')
        )
        
        return is_pbc_or_invitation and is_valid_format

    def download_document_tmp(self, document: object) -> str:
        if not document:
            raise ValidationError("document no puede estar vacío")
        
        if "url" not in document:
            raise ValidationError("document debe tener una URL")
        
        if "title" not in document:
            raise ValidationError("document debe tener un título")
        
        try:
            tmpdir = tempfile.mkdtemp()
            path = os.path.join(tmpdir, document["title"])
            
            response = requests.get(document["url"])
            response.raise_for_status()
            
            with open(path, "wb") as f:
                f.write(response.content)
            
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                raise DownloadError(f"El archivo descargado está vacío: {document['title']}")
            
            return path
            
        except requests.exceptions.RequestException as e:
            raise DownloadError(f"Error al descargar documento {document['title']}: {e}")
        except IOError as e:
            raise DownloadError(f"Error al guardar archivo {document['title']}: {e}")
        except Exception as e:
            raise DownloadError(f"Error inesperado al descargar {document['title']}: {e}")

    def check_document_mime_type(self, document: object) -> str:
        name = document["title"]
        if name.endswith(".pdf"):
            return "application/pdf"
        elif name.endswith(".doc"):
            return "application/msword"
        elif name.endswith(".docx"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif name.endswith(".zip"):
            return "application/zip"
        elif name.endswith(".rar"):
            return "application/x-rar-compressed"
        else:
            return ""

    def extract_pbc_from_zip(self, zip_path: str) -> str:
        """
        Extrae el archivo PBC o carta de invitación de un ZIP y lo guarda temporalmente.
        
        Args:
            zip_path: Path del archivo ZIP
            
        Returns:
            str: Path del archivo extraído en directorio temporal
            
        Raises:
            ValidationError: Si el path del ZIP es inválido
            ExtractionError: Si no se puede extraer el archivo o no se encuentra documento válido
        """
        if not zip_path:
            raise ValidationError("zip_path no puede estar vacío")
        
        if not os.path.exists(zip_path):
            raise ExtractionError(f"El archivo ZIP no existe: {zip_path}")
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Listar archivos en el ZIP
                file_list = zip_ref.namelist()
                
                if not file_list:
                    raise ExtractionError(f"El archivo ZIP está vacío: {zip_path}")
                
                # Buscar el archivo válido usando is_valid_document
                for filename in file_list:
                    # Extraer solo el nombre del archivo (sin directorios)
                    file_basename = os.path.basename(filename)
                    
                    if self.is_valid_document(file_basename):
                        # Crear directorio temporal
                        tmpdir = tempfile.mkdtemp()
                        
                        # Extraer el archivo al directorio temporal
                        zip_ref.extract(filename, tmpdir)
                        
                        # Construir el path completo del archivo extraído
                        extracted_path = os.path.join(tmpdir, filename)
                        
                        if not os.path.exists(extracted_path):
                            raise ExtractionError(f"Error al extraer {filename} del ZIP")
                        
                        return extracted_path
                
                # Si no se encontró ningún archivo válido
                basenames = [os.path.basename(f) for f in file_list]
                raise ExtractionError(
                    f"No se encontró documento PBC o carta de invitación en ZIP. "
                    f"Archivos disponibles: {', '.join(basenames)}"
                )
                
        except zipfile.BadZipFile:
            raise ExtractionError(f"El archivo no es un ZIP válido: {zip_path}")
        except FileNotFoundError:
            raise ExtractionError(f"El archivo ZIP no se encontró: {zip_path}")
        except PermissionError:
            raise ExtractionError(f"Sin permisos para acceder al archivo ZIP: {zip_path}")
        except Exception as e:
            raise ExtractionError(f"Error inesperado al extraer ZIP {zip_path}: {e}")

    def extract_pbc_from_rar(self, rar_path: str) -> str:
        """
        Extrae el archivo PBC o carta de invitación de un RAR y lo guarda temporalmente.
        
        Args:
            rar_path: Path del archivo RAR
            
        Returns:
            str: Path del archivo extraído en directorio temporal
            
        Raises:
            ValidationError: Si el path del RAR es inválido
            ExtractionError: Si no se puede extraer el archivo o no se encuentra documento válido
        """
        if not rar_path:
            raise ValidationError("rar_path no puede estar vacío")
        
        if not os.path.exists(rar_path):
            raise ExtractionError(f"El archivo RAR no existe: {rar_path}")
        
        try:
            # Configurar rarfile para usar unar en lugar de unrar
            rarfile.UNRAR_TOOL = "unar"
            
            with rarfile.RarFile(rar_path, 'r') as rar_ref:
                # Listar archivos en el RAR
                file_list = rar_ref.namelist()
                
                if not file_list:
                    raise ExtractionError(f"El archivo RAR está vacío: {rar_path}")
                
                # Buscar el archivo válido usando is_valid_document
                for filename in file_list:
                    # Extraer solo el nombre del archivo (sin directorios)
                    file_basename = os.path.basename(filename)
                    
                    if self.is_valid_document(file_basename):
                        # Crear directorio temporal
                        tmpdir = tempfile.mkdtemp()
                        
                        # Extraer el archivo al directorio temporal
                        rar_ref.extract(filename, tmpdir)
                        
                        # Construir el path completo del archivo extraído
                        extracted_path = os.path.join(tmpdir, filename)
                        
                        if not os.path.exists(extracted_path):
                            raise ExtractionError(f"Error al extraer {filename} del RAR")
                        
                        return extracted_path
                
                # Si no se encontró ningún archivo válido
                basenames = [os.path.basename(f) for f in file_list]
                raise ExtractionError(
                    f"No se encontró documento PBC o carta de invitación en RAR. "
                    f"Archivos disponibles: {', '.join(basenames)}"
                )
                
        except rarfile.BadRarFile:
            raise ExtractionError(f"El archivo no es un RAR válido: {rar_path}")
        except rarfile.NotRarFile:
            raise ExtractionError(f"El archivo no es un RAR: {rar_path}")
        except FileNotFoundError:
            raise ExtractionError(f"El archivo RAR no se encontró: {rar_path}")
        except PermissionError:
            raise ExtractionError(f"Sin permisos para acceder al archivo RAR: {rar_path}")
        except rarfile.RarExecError as e:
            raise ExtractionError(f"Error al ejecutar herramienta RAR: {e}")
        except Exception as e:
            raise ExtractionError(f"Error inesperado al extraer RAR {rar_path}: {e}")

    def convert_docx_to_pdf(self, docx_path: str) -> str:
        """
        Convierte un archivo DOCX a PDF usando pypandoc.
        
        Args:
            docx_path: Path del archivo DOCX a convertir
            
        Returns:
            str: Path del archivo PDF generado en directorio temporal
            
        Raises:
            ValidationError: Si el path del DOCX es inválido o no existe
            ConversionError: Si no se puede convertir el archivo a PDF
        """
        if not docx_path:
            raise ValidationError("docx_path no puede estar vacío")
        
        if not os.path.exists(docx_path):
            raise ConversionError(f"El archivo DOCX no existe: {docx_path}")
        
        try:
            # Configurar el PATH para incluir herramientas de LaTeX
            self._setup_conversion_environment()
            
            # Crear directorio temporal para el PDF
            tmpdir = tempfile.mkdtemp()
            
            # Generar nombre del archivo PDF
            docx_filename = os.path.basename(docx_path)
            pdf_filename = os.path.splitext(docx_filename)[0] + '.pdf'
            pdf_path = os.path.join(tmpdir, pdf_filename)
            
            # Intentar múltiples métodos de conversión
            conversion_methods = [
                ("pdflatex", lambda: pypandoc.convert_file(
                    docx_path, 
                    'pdf', 
                    outputfile=pdf_path,
                    extra_args=['--pdf-engine=pdflatex']
                )),
                ("pandoc default", lambda: pypandoc.convert_file(
                    docx_path, 
                    'pdf', 
                    outputfile=pdf_path
                )),
                ("via HTML", lambda: self._convert_via_html(docx_path, pdf_path)),
                ("weasyprint", lambda: self._convert_via_weasyprint(docx_path, pdf_path))
            ]
            
            errors = []
            for method_name, method in conversion_methods:
                try:
                    method()
                    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                        return pdf_path
                    else:
                        errors.append(f"{method_name}: PDF generado pero vacío")
                except Exception as e:
                    errors.append(f"{method_name}: {str(e)}")
            
            # Si llegamos aquí, ningún método funcionó
            raise ConversionError(
                f"No se pudo convertir {docx_path} a PDF. "
                f"Errores encontrados: {'; '.join(errors)}"
            )
                
        except Exception as e:
            if isinstance(e, ConversionError):
                raise
            raise ConversionError(f"Error inesperado al convertir {docx_path}: {e}")
    
    def _setup_conversion_environment(self) -> None:
        """
        Configura el entorno para la conversión de documentos
        """
        # Agregar rutas de LaTeX al PATH si no están presentes
        latex_paths = [
            '/Library/TeX/texbin',
            '/usr/local/texlive/2023/bin/universal-darwin',
            '/usr/local/texlive/2024/bin/universal-darwin',
            '/opt/homebrew/bin'
        ]
        
        current_path = os.environ.get('PATH', '')
        for latex_path in latex_paths:
            if os.path.exists(latex_path) and latex_path not in current_path:
                os.environ['PATH'] = f"{latex_path}:{current_path}"
                current_path = os.environ['PATH']
    
    def _convert_via_html(self, docx_path: str, pdf_path: str) -> None:
        """
        Método de conversión alternativo: DOCX → HTML → PDF
        """
        # Crear archivo HTML temporal
        tmpdir = os.path.dirname(pdf_path)
        html_path = os.path.join(tmpdir, 'temp.html')
        
        # Convertir DOCX a HTML
        pypandoc.convert_file(docx_path, 'html', outputfile=html_path)
        
        # Convertir HTML a PDF
        pypandoc.convert_file(html_path, 'pdf', outputfile=pdf_path)
    
    def _convert_via_weasyprint(self, docx_path: str, pdf_path: str) -> None:
        """
        Método de conversión usando weasyprint: DOCX → HTML → PDF
        """
        # Crear archivo HTML temporal
        tmpdir = os.path.dirname(pdf_path)
        html_path = os.path.join(tmpdir, 'temp.html')
        
        # Convertir DOCX a HTML
        pypandoc.convert_file(docx_path, 'html', outputfile=html_path)
        
        # Convertir HTML a PDF usando weasyprint
        try:
            import weasyprint
            weasyprint.HTML(filename=html_path).write_pdf(pdf_path)
        except ImportError:
            raise RuntimeError("weasyprint not available")

    def process_tender_documents(self, tender_id: Union[str, int], output_directory: str) -> str:
        """
        Método facade que procesa completamente los documentos de una licitación.
        
        Este método orquesta todo el flujo:
        1. Consulta la lista de documentos por ID
        2. Selecciona el documento correcto (PBC o carta de invitación)
        3. Lo descarga
        4. Lo procesa según su tipo (PDF, DOC/DOCX, ZIP, RAR)
        5. Convierte a PDF si es necesario
        6. Limpia archivos temporales
        7. Guarda el documento final en el directorio de salida
        
        Args:
            tender_id: ID de la licitación (puede ser str o int)
            output_directory: Directorio donde guardar el documento final
            
        Returns:
            str: Path del archivo PDF final, o cadena vacía si hay error
        """
        temp_files = []  # Lista para rastrear archivos temporales
        
        try:
            # Validar y convertir tender_id
            if tender_id is None:
                raise ValidationError("tender_id no puede ser None")
            
            tender_id_str = str(tender_id).strip()
            if not tender_id_str:
                raise ValidationError("tender_id no puede estar vacío")
            
            if not output_directory:
                raise ValidationError("output_directory no puede estar vacío")
            
            # Crear directorio de salida si no existe
            try:
                output_path = Path(output_directory)
                output_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValidationError(f"No se pudo crear directorio de salida {output_directory}: {e}")
            
            # 1. Consultar lista de documentos por ID
            documents = self.get_document_list(tender_id_str)
            
            # 2. Seleccionar el documento correcto
            selected_document = self.select_document(documents)
            
            document_title = selected_document["title"]
            
            # 3. Descargar el documento
            downloaded_path = self.download_document_tmp(selected_document)
            temp_files.append(downloaded_path)
            
            # 4. Procesar según el tipo de archivo
            final_pdf_path = self._process_downloaded_file(
                downloaded_path, 
                document_title, 
                output_path,
                temp_files
            )
            
            return final_pdf_path
                
        except (ValidationError, APIError, DocumentNotFoundError, DownloadError, 
                ExtractionError, ConversionError) as e:
            raise  # Re-lanzar excepciones conocidas
        except Exception as e:
            raise TCSDownloaderError(f"Error inesperado procesando tender {tender_id_str}: {e}")
            
        finally:
            # 6. Limpiar archivos temporales
            self._cleanup_temp_files(temp_files)

    def _process_downloaded_file(self, file_path: str, original_title: str, 
                                output_path: Path, temp_files: list) -> str:
        """
        Procesa el archivo descargado según su tipo.
        
        Args:
            file_path: Path del archivo descargado
            original_title: Título original del documento
            output_path: Directorio de salida
            temp_files: Lista para rastrear archivos temporales
            
        Returns:
            str: Path del archivo PDF final
        """
        # Determinar el tipo de archivo por extensión
        file_extension = Path(file_path).suffix.lower()
        base_name = Path(original_title).stem
        final_pdf_path = output_path / f"{base_name}.pdf"
        
        if file_extension == '.pdf':
            # 4.1. Si es PDF, copiarlo directamente
            try:
                shutil.copy2(file_path, final_pdf_path)
                return str(final_pdf_path)
            except Exception as e:
                raise TCSDownloaderError(f"Error al copiar PDF {file_path}: {e}")
            
        elif file_extension in ['.doc', '.docx']:
            # 4.2. Si es DOC/DOCX, convertir a PDF
            converted_pdf = self.convert_docx_to_pdf(file_path)
            temp_files.append(converted_pdf)
            try:
                shutil.copy2(converted_pdf, final_pdf_path)
                return str(final_pdf_path)
            except Exception as e:
                raise TCSDownloaderError(f"Error al copiar PDF convertido {converted_pdf}: {e}")
                
        elif file_extension == '.zip':
            # 4.3. Si es ZIP, extraer y procesar
            return self._process_compressed_file(
                file_path, 'zip', base_name, output_path, temp_files
            )
            
        elif file_extension == '.rar':
            # 4.4. Si es RAR, extraer y procesar
            return self._process_compressed_file(
                file_path, 'rar', base_name, output_path, temp_files
            )
            
        else:
            raise ValidationError(f"Tipo de archivo no soportado: {file_extension}")

    def _process_compressed_file(self, compressed_path: str, file_type: str,
                               base_name: str, output_path: Path, temp_files: list) -> str:
        """
        Procesa archivos comprimidos (ZIP/RAR).
        
        Args:
            compressed_path: Path del archivo comprimido
            file_type: Tipo de archivo ('zip' o 'rar')
            base_name: Nombre base para el archivo final
            output_path: Directorio de salida
            temp_files: Lista para rastrear archivos temporales
            
        Returns:
            str: Path del archivo PDF final
        """
        # Extraer el archivo correcto del comprimido
        if file_type == 'zip':
            extracted_path = self.extract_pbc_from_zip(compressed_path)
        elif file_type == 'rar':
            extracted_path = self.extract_pbc_from_rar(compressed_path)
        else:
            raise ValidationError(f"Tipo de archivo comprimido no soportado: {file_type}")
        
        temp_files.append(extracted_path)
        extracted_extension = Path(extracted_path).suffix.lower()
        final_pdf_path = output_path / f"{base_name}.pdf"
        
        if extracted_extension == '.pdf':
            # Si el extraído es PDF, copiarlo directamente
            try:
                shutil.copy2(extracted_path, final_pdf_path)
                return str(final_pdf_path)
            except Exception as e:
                raise TCSDownloaderError(f"Error al copiar PDF extraído {extracted_path}: {e}")
            
        elif extracted_extension in ['.doc', '.docx']:
            # Si el extraído es DOC/DOCX, convertir a PDF
            converted_pdf = self.convert_docx_to_pdf(extracted_path)
            temp_files.append(converted_pdf)
            try:
                shutil.copy2(converted_pdf, final_pdf_path)
                return str(final_pdf_path)
            except Exception as e:
                raise TCSDownloaderError(f"Error al copiar PDF convertido {converted_pdf}: {e}")
        else:
            raise ValidationError(f"El documento extraído no es un formato válido: {extracted_extension}")

    def _cleanup_temp_files(self, temp_files: list) -> None:
        """
        Limpia todos los archivos y directorios temporales.
        
        Args:
            temp_files: Lista de paths de archivos temporales
        """
        if not temp_files:
            return
            
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    if os.path.isfile(temp_file):
                        os.remove(temp_file)
                    elif os.path.isdir(temp_file):
                        shutil.rmtree(temp_file)
                        
                    # También limpiar el directorio padre si está vacío y es temporal
                    parent_dir = os.path.dirname(temp_file)
                    if parent_dir and '/tmp' in parent_dir and os.path.exists(parent_dir):
                        try:
                            if not os.listdir(parent_dir):  # Si está vacío
                                os.rmdir(parent_dir)
                        except OSError:
                            pass  # No pasa nada si no se puede eliminar
                            
            except OSError as e:
                pass  # Ignorar errores de limpieza

