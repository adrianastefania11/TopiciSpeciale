import os
import time
from datetime import datetime
from docling.document_converter import DocumentConverter
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import docling
import pandas as pd
from sqlalchemy import create_engine, text

# PostgreSQL setup
DB_USER = "pdf_user"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "pdf_data"
engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def extract_tables_from_pdf(pdf_path):
    print(pdf_path)
    try:

        # Open the document
        doc_converter = DocumentConverter()
        conv_res = doc_converter.convert(pdf_path)

        # Iterate through the tables in the document
        for table_ix, table in enumerate(conv_res.document.tables):
            # Export table data to a pandas DataFrame
            table_df = table.export_to_dataframe()

            print(f"## Table {table_ix}")
            print(table_df.to_markdown())

            invoice_id = save_invoice("1", pdf_path.split("\\")[1][:-4])
            table_df["invoice_id"] = invoice_id
            # Save the table data into PostgreSQL
            save_to_database(engine, table_df)

    except Exception as e:
        print(f"Error extracting tables from {pdf_path}: {e}")

# Watchdog event handler to watch for new files
class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".pdf"):
            print(f"New PDF detected: {event.src_path}")
            extract_tables_from_pdf(event.src_path)


def save_to_database(engine, table_df):
    # Clean up the DataFrame by renaming columns and converting types
    table_df.columns = ["Nr_crt", "Denumirea_produselor", "UM", "Cant", "Pret_unitar_fara_tva", "Valoare",
                        "Valoare_TVA", "invoice_id"]

    # Convert columns to appropriate types
    table_df["Nr_crt"] = table_df["Nr_crt"].astype(int)
    table_df["Cant"] = table_df["Cant"].astype(float)
    table_df["Pret_unitar_fara_tva"] = table_df["Pret_unitar_fara_tva"].replace(",", ".", regex=True).astype(float)
    table_df["Valoare"] = table_df["Valoare"].replace(",", ".", regex=True).astype(float)
    table_df["Valoare_TVA"] = table_df["Valoare_TVA"].replace(",", ".", regex=True).astype(float)

    # Save the DataFrame to PostgreSQL using to_sql
    table_df.to_sql("pdf_table", con=engine, if_exists='append', index=False)
    print("Data saved successfully to pdf_table.")

def save_invoice(user_id, invoice_number):
    with engine.connect() as connection:
        with connection.begin():  # Tranzacția va fi confirmată automat când ieși din blocul 'with'
            try:
                insert_query = """
                    INSERT INTO invoices (user_id, invoice_number)
                    VALUES (:user_id, :invoice_number)
                    RETURNING id;
                """
                params = {
                    "user_id": user_id,
                    "invoice_number": invoice_number
                }

                result = connection.execute(text(insert_query), params)

                invoice_id = result.fetchone()
                if invoice_id:
                    invoice_id = invoice_id[0]  # Extrage valoarea ID-ului

                    print(f"Factura a fost salvată cu ID-ul: {invoice_id}")
                    return invoice_id
                else:
                    print("Nu s-a putut salva factura: nu s-a returnat niciun ID.")
                    return None

            except Exception as error:
                print(f"Error la inserare: {error}")
                return None

def main():
    folder_to_watch = "watched_folder"
    os.makedirs(folder_to_watch, exist_ok=True)

    # Set up and start the observer
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)

    print(f"Watching folder: {folder_to_watch}")
    observer.start()

    try:
        while True:
            time.sleep(1)  # Keep the script running
    except KeyboardInterrupt:
        print("Stopping observer...")
        observer.stop()

    observer.join()

if __name__ == "__main__":
    main()
