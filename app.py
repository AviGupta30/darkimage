from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import numpy as np
import cv2
import base64
import io
import traceback # Import this for better error logging

# Import the main function AND the new helper
try:
    # We now import the helper function as well
    from enhancement import get_all_enhancements, _apply_hsv_brightening
    print("Successfully imported 'get_all_enhancements' and '_apply_hsv_brightening' from enhancement.py")
except ImportError:
    print("!!!!!!!!!!! ERROR IMPORTING ENHANCEMENT.PY !!!!!!!!!!!")
    get_all_enhancements = None
    _apply_hsv_brightening = None
except Exception as e:
    print(f"Error importing enhancement.py: {e}")
    get_all_enhancements = None
    _apply_hsv_brightening = None


# --- 1. FastAPI App Initialization ---
app = FastAPI()

# --- 2. Pydantic Model (Data Validation) ---
class ImageRequest(BaseModel):
    image_data: str

# --- 3. Helper Functions (Base64 Conversion - Unchanged) ---
def base64_to_cv2(base64_string: str) -> np.ndarray:
    """Converts a base64 string (from JS) to an OpenCV image (BGR)."""
    try:
        if "," in base64_string:
            base64_string = base64_string.split(',')[1] # Strip header
        
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        cv2_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if cv2_image is None:
            raise ValueError("cv2.imdecode failed to decode image data.")
        if len(cv2_image.shape) == 2:
            cv2_image = cv2.cvtColor(cv2_image, cv2.COLOR_GRAY2BGR)

        return cv2_image
        
    except Exception as e:
        print(f"Error decoding base64: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

def cv2_to_base64(cv2_image: np.ndarray) -> str:
    """Converts an OpenCV image (BGR) back to a base64 string (for JS)."""
    try:
        is_success, buffer = cv2.imencode(".jpeg", cv2_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        if not is_success:
            raise ValueError("cv2.imencode failed to encode image data.")

        base64_string = base64.b64encode(buffer).decode('utf-8')
        return "data:image/jpeg;base64," + base64_string
    except Exception as e:
        print(f"Error encoding base64: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {e}")

# --- 4. API Endpoint (MODIFIED) ---
@app.post("/enhance")
async def enhance_api(request: ImageRequest):
    """
    This API endpoint now runs the enhancement iteratively
    and returns all three results, PLUS the pipeline flag.
    """
    if get_all_enhancements is None:
        print("ERROR: /enhance called but get_all_enhancements function is not loaded.")
        raise HTTPException(status_code=500, detail="Enhancement function not loaded. Check server logs.")
        
    try:
        print("--- /enhance endpoint called ---")
        # 1. Decode image from Base64 to OpenCV image
        original_cv2_image = base64_to_cv2(request.image_data)
        
        # 2. Apply the iterative enhancement
        # This new function returns 4 items
        img_1x, img_2x, img_3x, pipeline = get_all_enhancements(original_cv2_image)
        
        # 3. Encode all three enhanced images back to Base64
        b64_1x = cv2_to_base64(img_1x)
        b64_2x = cv2_to_base64(img_2x)
        b64_3x = cv2_to_base64(img_3x)
        
        print(f"--- Sending all 3 images and pipeline flag '{pipeline}' back to frontend ---")
        # 4. Send them all back to the frontend in one JSON object
        return {
            "enhanced_1x": b64_1x,
            "enhanced_2x": b64_2x,
            "enhanced_3x": b64_3x,
            "pipeline": pipeline # Send the pipeline flag
        }
        
    except Exception as e:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"FATAL ERROR during /enhance: {e}")
        traceback.print_exc() # This will print the full red error message
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        raise HTTPException(status_code=500, detail=f"Enhancement failed: {e}")

# --- 5. NEW API ENDPOINT ---
@app.post("/brighten")
async def brighten_api(request: ImageRequest):
    """
    Applies an additional brightening boost to an *existing* image.
    We use a 1.25x factor (a 25% increase).
    """
    if _apply_hsv_brightening is None:
        print("ERROR: /brighten called but _apply_hsv_brightening function is not loaded.")
        raise HTTPException(status_code=500, detail="Brightening function not loaded.")
        
    try:
        print("--- /brighten endpoint called ---")
        cv2_image = base64_to_cv2(request.image_data)
        
        brightened_image = _apply_hsv_brightening(
            cv2_image, 
            brightening_factor=1.25 # This is the 0.25 increase
        )
        
        b64_brightened = cv2_to_base64(brightened_image)
        
        print("--- Sending brightened image back ---")
        return {
            "brightened_image": b64_brightened
        }

    except Exception as e:
        print(f"FATAL ERROR during /brighten: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Brightening failed: {e}")

# --- 6. NEW API ENDPOINT (CORRECTED) ---
@app.post("/darken")
async def darken_api(request: ImageRequest):
    """
    Applies an additional darkening effect to an *existing* image.
    We use a 0.75x factor (a 25% decrease).
    """
    if _apply_hsv_brightening is None:
        print("ERROR: /darken called but _apply_hsv_brightening function is not loaded.")
        raise HTTPException(status_code=500, detail="Darkening function not loaded.")
        
    try:
        print("--- /darken endpoint called ---")
        cv2_image = base64_to_cv2(request.image_data)
        
        # Call the same function, but with a factor < 1
        darkened_image = _apply_hsv_brightening(
            cv2_image, 
            brightening_factor=0.75 # This is the 25% decrease
        )
        
        b64_darkened = cv2_to_base64(darkened_image)
        
        print("--- Sending darkened image back ---")
        # --- THIS IS THE CRITICAL LINE ---
        # Ensure the key is "darkened_image"
        return {
            "darkened_image": b64_darkened
        }

    except Exception as e:
        print(f"FATAL ERROR during /darken: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Darkening failed: {e}")


# --- 7. Mount Static Files ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")

print("FastAPI server setup is complete.")
# To run: uvicorn app:app --reload