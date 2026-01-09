import sqlite3
import pickle
import os
import gc
import shutil
from tqdm import tqdm
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


class ReceiptDB():
    """Setup the full sql and vector databases for the receipts"""

    def __init__(
            self,
            sql_db_path,
            sql_db,
            vector_db_path,
            vector_db_name,
            full_receipt_details = "assets/full_receipt_details.pkl"
            ):
        
        with open(full_receipt_details, "rb") as f:
            self.full_receipt_details = pickle.load(f)
        self.sql_db_path = sql_db_path  #"db/receipts_sql_db"
        self.sql_db = sql_db    #"db/receipts_sql_db/receipts.db"
        self.vector_db_path = vector_db_path    #"db/receipts_vector_db"
        self.vector_db_name= vector_db_name     #"receipts"
        self.embeddings = HuggingFaceEmbeddings(
            model_name= "C:\\Users\HomePC\Desktop\Python\deep_learning_ai\langchain_intro\models\\all-MiniLM-L6-v2",
            encode_kwargs = {"normalize_embeddings": True}
        )
        self.vectorstore= Chroma(
            embedding_function= self.embeddings,
            persist_directory= self.vector_db_path,
            collection_name=self.vector_db_name
        )

    def create_sql_db(self, db_path=None):
        """Setup the structure of the sql databse & create necessary tables"""
        if db_path is None:
            db_path= self.sql_db_path

        if not os.path.exists(db_path): #create the db path if it doesn't exist
            os.makedirs(db_path)

        with sqlite3.connect(self.sql_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS receipts(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_number TEXT,
                    date TEXT,
                    vendor_name TEXT NOT NULL,
                    tax REAL,
                    subtotal REAL,
                    total REAL,
                    payment_method TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    additional_information TEXT
                )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS line_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER NOT NULL,
                description TEXT,
                quantity INT DEFAULT 1, 
                unit_price REAL,
                total_price REAL NOT NULL,
                FOREIGN KEY (receipt_id) REFERENCES receipts(id)
            )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vendor ON receipts(vendor_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_total ON receipts(total)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON receipts(date)")

            conn.commit()
        print(f"Sql database successfully created at {db_path}")


    def store_receipt(self, sql_db=None):
        """Insert the receipt details to the database"""
        if sql_db is None:
            sql_db = self.sql_db
        self.create_sql_db()
        
        with sqlite3.connect(self.sql_db) as conn:
            cursor = conn.cursor()
            for receipt in tqdm(self.full_receipt_details, desc="Creating receipts db..."):
                cursor.execute("""
                        INSERT INTO receipts(
                        vendor_name, date, total, receipt_number, tax, subtotal, payment_method, additional_information
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            receipt.get('vendor_name'),
                            receipt.get('date'),
                            receipt.get('total', 0),
                            receipt.get('receipt_number'),
                            receipt.get('tax'),
                            receipt.get('subtotal'),
                            receipt.get('payment_method'),
                            receipt.get('additional_information'),
                        )
                    )

                receipt_id = cursor.lastrowid

                items = receipt.get("items", [])
                for item in items:
                        cursor.execute("""
                            INSERT INTO line_items(
                                receipt_id, description, quantity, unit_price, total_price
                            )
                            VALUES (?, ?, ?, ?, ?)
                        """, 
                            (
                                receipt_id,
                                item.get("description", ""),
                                item.get("quantity", 1),
                                item.get("unit_price"),
                                item.get("total_price", 0)
                            )          
                        )

                self.create_vector_db(receipt=receipt, receipt_id=receipt_id)

                conn.commit()
        print(f"Vector database successfully created at {self.vector_db_path}")

    
    def create_vector_db(self,  receipt, receipt_id, vector_db_path=None,):
        """Create embeddings and store to the vector database"""
        if not vector_db_path:
            vector_db_path = self.vector_db_path

        if not os.path.exists(vector_db_path): #create the db path if it doesn't exist
            os.makedirs(vector_db_path)

        detailed_text = f"""
            Vendor: {receipt.get("vendor_name", "Unknown")}
            Date: {receipt.get("date")}
            Items: {[item.get("description") for item in receipt.get("items")]}
            Total: {receipt.get("total", 1)}
        """.strip()

        doc = Document(
            page_content=detailed_text,
            metadata = {
                "receipt_id": receipt_id,
                "date": receipt.get("date"),
                "vendor": receipt.get("vendor_name", "Unknown"),
                "total": receipt.get("total", 0)
            }
        )
        self.vectorstore.add_documents([doc])

    def view_sql_db(self, sql_db=None, receipts_only=True):
        """View the content of the receipt db"""
        if sql_db is None:
            sql_db =self.sql_db
        with sqlite3.connect(sql_db) as conn:
            cursor = conn.cursor()
            if receipts_only:
                cursor.execute("SELECT * FROM receipts")
            else:
                cursor.execute("SELECT * FROM line_items")
        return cursor.fetchall()

    def delete_sql_db(self, sql_db=None):
        """Delete the receipts and line_items tables in the sql database"""
        if sql_db is None:
            sql_db =self.sql_db
        with sqlite3.connect(sql_db) as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS receipts")
            cursor.execute("DROP TABLE IF EXISTS line_items")
        conn.commit()
    
    def delete_vector_db(self, vector_db_path=None):
        """Delete the vector database"""
        if vector_db_path is None:
            vector_db_path= self.vector_db_path
        
        if os.path.exists(vector_db_path):
            shutil.rmtree(vector_db_path)
            print(f"Vector database at {vector_db_path} successfully deleted")
        else:
            print(f"Vector database at {vector_db_path} does not exist")

        

    # def store_reciept_to_vector_db(self):
        # detailed_text = f"""
        #     Vendor: {receipt.get("vendor_name", "Unknown")}
        #     Date: {receipt.get("date")}
        #     Items: {[item.get("description") for item in receipt.get("items")]}
        #     Total: {receipt.get("total", 1)}
        # """.strip()
        # doc = Document(
        #     page_content=detailed_text,
        #     metadata = {
        #         "receipt_id": receipt_id,
        #         "date": receipt.get("date"),
        #         "vendor": receipt.get("vendor_name", "Unknown"),
        #         "total": receipt.get("total_price", 0)
        #     }
        # )
        # self.vectorstore.add_documents([doc])
    
    def retrieve_docs_from_db(self, query, num_matches=5):
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": num_matches*10})
        response = retriever.invoke(query)
        seen_ids = set()
        unique_res = []

        for doc in response:
            receipt_id= doc.metadata['receipt_id']
            if receipt_id not in seen_ids:
                seen_ids.add(receipt_id)
                unique_res.append(doc)
            if len(unique_res)>=num_matches:
                break

        unique_ids = [r.metadata['receipt_id'] for r in unique_res]

        with sqlite3.connect(self.sql_db) as conn:
            cursor = conn.cursor()
            matched_receipts, matched_items =[], []
            for receipt_id in unique_ids:
                cursor.execute("SELECT * FROM receipts where id = ?", (receipt_id,))
                receipt = cursor.fetchone()
                matched_receipts.append(receipt)
                cursor.execute("SELECT * FROM line_items where receipt_id = ?", (receipt_id,))
                item = cursor.fetchone()
                matched_items.append(item)
        return matched_receipts, matched_items
