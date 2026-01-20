from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import numpy as np
import cv2
import base64
import os
import shutil
import uuid
import traceback

try:
    from enhancement import get_all_enhancements, _apply_hsv_brightening
    from video_enhancement import process_video_smartly
    print("SUCCESS: Loaded enhancement modules.")
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import enhancement modules. {e}")
    get_all_enhancements = None
    _apply_hsv_brightening = None
    process_video_smartly = None

app = FastAPI()

UPLOAD_DIR = "static/uploads"
RESULT_DIR = "static/results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

class ImageRequest(BaseModel):
    image_data: str

def base64_to_cv2(base64_string: str) -> np.ndarray:
    try:
        if "," in base64_string:
            base64_string = base64_string.split(',')[1]
        
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        cv2_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if cv2_image is None:
            raise ValueError("cv2.imdecode failed.")
        return cv2_image
        
    except Exception as e:
        print(f"Error decoding base64: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

def cv2_to_base64(cv2_image: np.ndarray) -> str:
    try:
        _, buffer = cv2.imencode(".jpeg", cv2_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        base64_string = base64.b64encode(buffer).decode('utf-8')
        return "data:image/jpeg;base64," + base64_string
    except Exception as e:
        print(f"Error encoding base64: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {e}")

@app.post("/enhance")
async def enhance_api(request: ImageRequest):
    if get_all_enhancements is None:
        raise HTTPException(status_code=500, detail="Enhancement function not loaded.")
        
    try:
        print("--- /enhance endpoint called ---")
        original_cv2_image = base64_to_cv2(request.image_data)
        
        img_1x, img_2x, img_3x, pipeline = get_all_enhancements(original_cv2_image)
        
        return {
            "enhanced_1x": cv2_to_base64(img_1x),
            "enhanced_2x": cv2_to_base64(img_2x),
            "enhanced_3x": cv2_to_base64(img_3x),
            "pipeline": pipeline
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Enhancement failed: {e}")

@app.post("/brighten")
async def brighten_api(request: ImageRequest):
    if _apply_hsv_brightening is None:
        raise HTTPException(status_code=500, detail="Function not loaded.")
        
    try:
        cv2_image = base64_to_cv2(request.image_data)
        brightened_image = _apply_hsv_brightening(cv2_image, brightening_factor=1.25)
        return {"brightened_image": cv2_to_base64(brightened_image)}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Brightening failed: {e}")

@app.post("/darken")
async def darken_api(request: ImageRequest):
    if _apply_hsv_brightening is None:
        raise HTTPException(status_code=500, detail="Function not loaded.")
        
    try:
        cv2_image = base64_to_cv2(request.image_data)
        darkened_image = _apply_hsv_brightening(cv2_image, brightening_factor=0.75)
        return {"darkened_image": cv2_to_base64(darkened_image)}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Darkening failed: {e}")

@app.post("/enhance-video")
async def enhance_video_endpoint(file: UploadFile = File(...)):
    if process_video_smartly is None:
        raise HTTPException(status_code=500, detail="Video function not loaded.")

    input_path = None
    try:
        filename = f"{uuid.uuid4()}_{file.filename}"
        input_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        output_filename = f"enhanced_{filename}"
        output_path = os.path.join(RESULT_DIR, output_filename)
        
        print(f"Processing video: {filename}")
        process_video_smartly(input_path, output_path, sample_rate=4)
        
        video_url = f"/results/{output_filename}"
        return {"video_url": video_url}

    except Exception as e:
        print(f"Video Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Video processing failed: {e}")
    finally:
        if input_path and os.path.exists(input_path):
            try:
                os.remove(input_path)
            except:
                pass

app.mount("/results", StaticFiles(directory="static/results"), name="results")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

print("FastAPI server ready.")