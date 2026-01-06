import os
import cv2
import pytesseract
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from zipfile import ZipFile
from pathlib import Path
from IPython.display import Markdown, display
from typing import Optional, Union, Tuple
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
        rotated = cv2.warpAffine(denoised, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


        if plot_img:
            _= plt.figure(figsize=(14,8))
            plt.imshow(rotated, cmap="gray")
            plt.axis("off")
            plt.title(f"CV2: {img_path}")
            # cv2.imshow("Preprocessed img", rotated)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()
        return rotated
    

    def pil_cv2_preprocess(self, img_path=None, use_random_img=False, plot_steps=False):
        if use_random_img:
            img_path = self.get_random_image_path()
        elif img_path is None:
            raise ValueError("No image path provided")

        img = Image.open(img_path)
        img = img.convert("L")
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)

        target_width = 1500
        scale = target_width / img.width
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)

        cv_img = np.array(img)
        denoised = cv2.fastNlMeansDenoising(cv_img, None, 10, 7, 21)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if cv2.countNonZero(binary) > (binary.size / 2):
            binary = cv2.bitwise_not(binary)

        coords = np.column_stack(np.where(binary > 0))
        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = denoised.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        final_img = cv2.warpAffine(denoised, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        # --- PHASE 3: Visual Check ---
        if plot_steps:
            plt.figure(figsize=(12, 6))

            plt.subplot(1, 2, 2)
            plt.title(f"Hybrid({angle:.2f}°)")
            plt.imshow(final_img, cmap='gray')
            plt.axis('off')
            
            plt.show()

        return final_img
    
    def use_all_preprocessors(self, img_path, plot_images=False):
        pil_img = self.pil_preprocess(img_path)
        cv2_img = self.cv2_preprocess(img_path)
        master_img = self.pil_cv2_preprocess(img_path)

        processed_images = [pil_img, cv2_img, master_img]
        fig, ax = plt.subplots(figsize=(14, 7), nrows=1, ncols=3)

        if plot_images:
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
        """Use tesseract to extract the image contents"""
        img_contents= pytesseract.image_to_string(proccessed_img)
        return img_contents
    
receipt_ocr = ReceiptOCR()
receipt_ocr.get_random_image_path()