import sys
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from modules.pdf_reader.pdf_reader import PDFReader
from dotenv import load_dotenv

class ItemExtractor:
    def __init__(self, pdf_path):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.pdf_path = pdf_path
        self.system_message = """
        Te voy a pasar páginas del pliego de bases y condiciones de una licitación. La información de las páginas están organizadas en tres partes:
        1 - Texto plano: Todo el texto plano que se pudo extraer del pdf
        2 - Tablas Lattice: Las tablas con bordes que se pudieron detectar del pdf las columnas están separadas por "\t|\t" y las filas por "-"*30
        3 - Tablas Stream: Las tablas sin bordes que se pudieron detectar del pdf las columnas están separadas por "\t|\t" y las filas por "-"*30

        Necesito que identifiques si en la página están presentes items licitados (atendiendo que no se de condiciones del oferente ) y de ser así, que los enlistes y extraigas sus caracteristicas en este formato:

        Nombre: <nombre del item>
        Unidad de medida: <unidad de medida del item>
        Cantidad solicitada: <cantidad solicitada del item>
        <caracteristica 1>: <valor de la caracteristica 1>
        <caracteristica 2>: <valor de la caracteristica 2>
        .
        .
        <caracteristica n>: <valor de la caracteristica n>

        Ten en cuenta que en la descripción misma de los ítems puede haber características que sirvan para clasificar el ítems, intenta extraer y estructurar toda la información que se pueda de los ítems de modo a luego poder compararlos por estas características. No te quedes solo con estructuras, clasificaciones y formatos dados por el documento.

        No pongas limitaciones en el listado de los items, necesito que traigas todos los ítems sin importar la cantidad.

        Un item generalmente tiene unidad de medida, cantidad solicitada. No todo lo que está en una tabla es un ítem. Por favor, tráeme solo lo que tengas una confianza mayor al 80% de que es un ítem de licitación.
        """

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_message),
            ("user", "Extrae los items de la siguiente página: \n\n {text_input}")
        ])
        self.llm = ChatOpenAI(model="gpt-4o-mini")

    def extract_items(self, text_input):
        prompt = self.prompt.format_messages(text_input=text_input)
        response = self.llm.invoke(prompt)
        return response.content

    def extract_items_from_pdf(self):
        pdf_reader = PDFReader(self.pdf_path)
        pdf_text = pdf_reader.read_pdf_as_markdown()
        return self.extract_items(pdf_text)

def main():
    if len(sys.argv) != 2:
        print("Usage: item-extractor <pdf_file_path>")
        sys.exit(1)
    pdf_path = sys.argv[1]
    load_dotenv()
    item_extractor = ItemExtractor(pdf_path)
    items = item_extractor.extract_items_from_pdf()
    print(items)


if __name__ == "__main__":
    main()