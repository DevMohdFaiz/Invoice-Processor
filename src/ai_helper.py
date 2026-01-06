import os
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import List, Optional


def llm_parser(raw_text):
    class LineItem(BaseModel):
        """A single item on the receipt"""
        description: str = Field(description="The name of the items/ decription")
        quantity: Optional[int] = Field(default=1, description="Qunatity Purchased")
        unit_price: int = Field(default=None, description="Price of a single unit of this line item")
        total_price: float = Field(description="Total price of this line item")

    class Receipt(BaseModel):
        """Structured Receipt Data"""
        
        vendor_name: str = Field(description="Name of the Store or vendor")
        date: Optional[str] = Field(description="Date of the purchase in DD-MM-YYY format")
        total: float = Field(description="Total amount of the purchase")
        receipt_number: Optional[str] = Field(default=None, description="Receipt/invoice number")
        tax: Optional[float] = Field(default=None, description="Tax amount")
        subtotal: Optional[float] = Field(default=None, description="Subtotal before tax")
        payment_method: Optional[str] = Field(default=None, description="Payment method (cash/card)")

        items: List[LineItem] = Field(description="List of items purchased")
        additional_information: Optional[dict] = Field(description="Any additional relevant information")

    class MultipleReceipt(BaseModel):
        receipts: List[Receipt] = Field(description="All the extracted receipts")

    prompt = ChatPromptTemplate.from_template("""
        You are an expert at extracting structured data from receipts and invoices.

        Extract information from this receipt text. The text is from TesseractOCR so it may be messy, 
        have errors, or be poorly formatted.

        **RULES:**
        1. Extract whatever fields you can find
        2. If a field is not present, set it to null
        3. For dates, convert to DD-MM-YYYY format
        4. Remove currency symbols from amounts (extract numbers only)
        5. If you see gibberish or unclear text, skip it
        6. Be flexible with field names (e.g., "Store" = "Shop" = "Vendor")
        7. Items might be in different formats - be flexible
        8. If product quantity is not specified, assume 1

        **Common OCR errors to handle:**
        - "O" might be "0" in numbers
        - "l" might be "1" in numbers
        - Spaces might be missing or extra
        - Lines might be in wrong order

                                            
        The input data, raw_text is in a python dictionary format. 
        The dictionary keys represent the index of each receipt while the dictionary values represent the raw text extracted via OCR
        
                                            
        Receipt text:
        {raw_text}

        {format_instructions}
        Your output should be in the format:
        You must **explicitly** Return ONLY valid JSON, nothing else.
        DO NOT ADD ANYTHING ELSE TO THE JSON
    """)


    llm = ChatGroq(api_key=os.environ["GROQ_API_KEY"], model="openai/gpt-oss-120b", temperature=0)
    json_parser = JsonOutputParser(pydantic_object=MultipleReceipt)

    chain = prompt | llm | json_parser
    llm_response = chain.invoke({
        "raw_text": raw_text,
        "format_instructions": json_parser.get_format_instructions()
    })

    return llm_response