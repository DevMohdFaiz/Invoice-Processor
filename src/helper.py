import os
import cv2
import easyocr
import pytesseract
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from zipfile import ZipFile
from pathlib import Path
from IPython.display import Markdown, display
from typing import Optional, Union, List
from tqdm import tqdm

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class ReceiptOCR:
    """Process random image"""

    def __init__(self):
        self.data_dir = Path("invoices_dataset/invoices")
        self.images = os.listdir(self.data_dir)

    def plot_image(self, img: Union[str, np.array]):
        try:
            img = Image.open(img)
            plt.title(img)
        except:
            plt.imshow(img, cmap="gray")
            plt.title("")
        plt.axis("off")
        # plt.show()

    def get_random_image_path(self):
        """Get a random image from the dataset"""
        random_img = self.images[np.random.randint(0, len(self.images))]
        return self.data_dir/random_img
    
    def pil_preprocess(self, img_path=None, plot_img=False, use_random_img=False):
        """Preprocess a random image or user image via `PIL` library"""
        if use_random_img:
            img_path = self.get_random_image_path()
        else:
            if img_path is None:
                raise ValueError(f"Image path cannot be {type(img_path)}")
        
        img = Image.open(img_path)
        img_trans= img.convert("L")
        enhancer = ImageEnhance.Contrast(img_trans)
        img_trans = enhancer.enhance(2)
        img_trans = img_trans.filter(ImageFilter.SHARPEN)
        # img_trans.filter(ImageFilter.SMOOTH)
        resizing_scale = 1500/ img_trans.width
        new_img_size = (int(img_trans.width*resizing_scale), int(img_trans.height*resizing_scale)) #forces the image width to be 1k
        img_trans = img_trans.resize((new_img_size), Image.LANCZOS)
    
        if plot_img:
            fig = plt.figure(figsize=(10, 8))
            plt.imshow(img_trans, cmap="gray")
            plt.axis("off")
            plt.title(f"PIL: {img_path}");       
        
        return np.array(img_trans)
    
    def cv2_preprocess(self, img_path=None, use_random_img=False, plot_img=False):
        if use_random_img:
            img_path = self.get_random_image_path()
        else:
            if img_path is None:
                raise ValueError(f"Image path cannot be {type(img_path)}")
        
        img = cv2.imread(img_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        if cv2.countNonZero(binary) > (binary.size / 2):
            binary = cv2.bitwise_not(binary)

        coords = np.column_stack(np.where(binary > 0))
        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        (h, w) = binary.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(denoised, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
        final_img = cv2.cvtColor(rotated, cv2.COLOR_GRAY2RGB)


        if plot_img:
            _= plt.figure(figsize=(14,8))
            plt.imshow(final_img, cmap="gray")
            plt.axis("off")
            plt.title(f"CV2: {img_path}")
        return final_img
    

    def pil_cv2_preprocess(self, img_path=None, use_random_img=False, plot_steps=False):
        if use_random_img:
            img_path = self.get_random_image_path()
        elif img_path is None:
            raise ValueError("No image path provided")

        img = Image.open(img_path)
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            alpha = img.convert('RGBA').split()[-1]
            bg = Image.new("RGB", img.size, (255, 255, 255, 255))
            bg.paste(img.convert('RGBA'), mask=alpha)
            img = bg

        img = img.convert("L")
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)

        target_width = 1500
        if img.width < target_width:
            scale = target_width / img.width
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.LANCZOS)
        
        cv_img = np.array(img)
        denoised = cv2.fastNlMeansDenoising(cv_img, None, 10, 7, 21)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mean_val = np.mean(binary)
        if mean_val < 128:  
            binary = cv2.bitwise_not(binary)
        final_img = denoised  

        if plot_steps:
            plt.figure(figsize=(12, 6))
            plt.subplot(1, 2, 2)
            plt.title(f"Processed")
            plt.imshow(final_img, cmap='gray')
            plt.axis('off')            
            plt.show()

        return Image.fromarray(final_img)
    
    def use_all_preprocessors(self, img_path=None, use_random_image=False, plot_images=False):
        """Preprocess image via pil, cv and pil_cv"""
        if use_random_image:
            img_path = self.get_random_image_path()
        pil_img = self.pil_preprocess(img_path)
        cv2_img = self.cv2_preprocess(img_path)
        master_img = self.pil_cv2_preprocess(img_path)

        processed_images = [pil_img, cv2_img, master_img]

        if plot_images:
            _, ax = plt.subplots(figsize=(14, 7), nrows=1, ncols=3)
            plt.axis("off")
            plt.sca(ax[0])
            _=self.plot_image(processed_images[0])
            ax[0].set_title(f"PIL")

            plt.sca(ax[1])
            _=self.plot_image(processed_images[1])
            ax[1].set_title(f"CV2")

            plt.sca(ax[2])
            _=self.plot_image(processed_images[2])
            ax[2].set_title(f"PIL & CV2")
            plt.show();

        return processed_images
    
    def ocr_with_tesseract(self, proccessed_img):
        """Use tesseract to extract the receipt contents"""
        img_contents= pytesseract.image_to_string(proccessed_img)
        return img_contents
    
    def ocr_with_easyocr(processed_images: List):
        """Use easyocr to extract receipt contents"""
        easy_reader = easyocr.Reader(["en"], gpu=False)
        results = []
        for img in tqdm(processed_images, desc="Analyzing images..."):
            if isinstance(img, Image.Image):
                img_array =np.array(img)
            else:
                img_array = img
            if len(img_array.shape)== 2:
                pass
            elif img_array.shape[2]== 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            result = easy_reader.readtext(img_array)
            results.append(result)

        return results
