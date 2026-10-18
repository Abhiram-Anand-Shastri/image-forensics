import numpy, scipy, PIL, cv2, skimage, matplotlib
import exifread, imagehash, reportlab, streamlit

print("NumPy:", numpy.__version__)
print("Pillow:", PIL.__version__)
print("OpenCV:", cv2.__version__)
print("scikit-image:", skimage.__version__)
print("SIFT available:", hasattr(cv2, "SIFT_create"))
print("All libraries imported successfully")