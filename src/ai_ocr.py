import base64
import shutil
import os
from PIL import Image
from tqdm import tqdm
from langchain_groq import ChatGroq
from pydantic import Field, BaseModel
from typing import Optional, List
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

from config import GROQ_API_KEY

class GroqProcessor():
    """Extract receipt details via a Large Vision Model"""

    def __init__(
            self,
            model = "meta-llama/llama-4-scout-17b-16e-instruct"
            ):        
        self.llm = ChatGroq(api_key=GROQ_API_KEY, model=self.model, temperature=0)

    def optimize_image_for_lvm(self, original_image_path, optimized_image_path, max_img_size=1024):
            """Optimize user image before sending to lvm"""
            img= Image.open(original_image_path).convert("RGB")
            # opt_img_path = os.path.join(optimized_image_path, img_path)
            if max(img.size) > max_img_size:
                ratio = max_img_size / max(img.size)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                opt_img = img.resize(new_size, Image.LANCZOS)
                opt_img.save(optimized_image_path, optimize=True, quality=85)
            else:
                img.save(optimized_image_path, optimize=True, quality=85)

    def optimize_images_for_lvm(self, original_images_path, optimized_images_path):
        """Optimize multiple images before sending to lvm"""
        orig_images = os.listdir(original_images_path)
        opt_images = os.listdir(optimized_images_path)

        if os.path.exists(optimized_images_path) and (len(opt_images) == len(orig_images)):
            return f"{optimized_images_path} already exists and is complete"
        elif os.path.exists(optimized_images_path) and (len(opt_images) != len(orig_images)):
            shutil.rmtree(optimized_images_path)
            os.makedirs(optimized_images_path)
        elif not(os.path.exists(optimized_images_path)):
            os.makedirs(optimized_images_path)        
        
        for img_path in tqdm(orig_images, desc="Optimizing images for LVM..."):
            optimized_image_path = os.path.join(optimized_images_path, img_path)
            self.optimize_image_for_lvm(img_path, optimized_image_path)
        

    def encode_image_tobase64(self, image_path):
        """Convert user Image to base64 string"""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    def extract_receipt_data(self, image_path):
        """
        Send user receipt image to groq API for extraction if the details
        Args:
            image_path:str = system path of the user image
        """
        base64_image = self.encode_image_tobase64(image_path)
        class LineItem(BaseModel):
            """A single item on the receipt"""
            description: str = Field(description="The name of the items/ decription")
            quantity: Optional[int] = Field(default=1, description="Quantity Purchased")
            unit_price: float = Field(default=None, description="Price of a single unit of this line item")
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

        json_parser = JsonOutputParser(pydantic_object= Receipt)

        prompt = f"""
            You are an expert at extracting structured data from receipts.

            Extract all information from this receipt image and return your answer as a JSON.

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
            
            Your output should be in the format:
            {json_parser.get_format_instructions()}
                                                
            You must **explicitly** Return ONLY valid JSON, nothing else.
            DO NOT ADD ANYTHING ELSE TO THE JSON
        """

        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url", 
                "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
            }
        ])
        try:
            response = self.llm.invoke([message])
            parsed_response = json_parser.parse(response.content)
            return parsed_response
        except Exception as e:
            print(f"Encountered an error during extraction: {e}")
            return {
                "vendor_name": "Unknown",
                "error": e
            }
    
    # def batch_extract_receipt(image_paths):

