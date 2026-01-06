import sqlite3
import pickle



class ReceiptDB():
    """Setup the full sql database for the receipts"""

    def __init__(self):
        with open("assets/full_receipt_details.pkl", "rb") as f:
            self.full_receipt_details = pickle.load(f)
        self.sql_db_path = "db/receipts_sql_db/receipts.db"

    def create_sql_db(self, db_path=None):
        """Setup the structure of the sql databse & create necessary tables"""
        if db_path is None:
            db_path= self.sql_db_path

        with sqlite3.connect(db_path) as conn:
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
        print(f"Database successfully created at {db_path}")


    def store_receipt(self, db_path=None):
        """Insert the receipt details to the database"""
        if db_path is None:
            db_path = self.sql_db_path

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            for receipt in self.full_receipt_details:
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

                for receipt in self.full_receipt_details:
                    items = receipt.get("items", {})
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
                conn.commit()

    
    def delete_db(self, db_path="db/receipts+sql_db/receipts.db"):
        cursor = 
