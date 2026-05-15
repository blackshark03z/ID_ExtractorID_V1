import fitz # PyMuPDF
import os

def extract_images_from_pdf(pdf_path, output_dir):
    """
    Extracts all images from a PDF file and saves them to output_dir.
    Returns a list of saved image paths.
    """
    saved_paths = []
    try:
        doc = fitz.open(pdf_path)
        for page_index in range(len(doc)):
            page = doc[page_index]
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Check if it's a valid image and not too small (ignore tiny icons/lines)
                if len(image_bytes) > 5000: 
                    img_name = f"extracted_pdf_{page_index}_{img_index}.{image_ext}"
                    img_path = os.path.join(output_dir, img_name)
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    saved_paths.append(img_path)
    except Exception as e:
        print(f"  Lỗi khi giải nén PDF {pdf_path}: {e}")
        
    return saved_paths
