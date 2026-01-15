import cv2
import numpy as np
import traceback
import pywt  # Required for Discrete Wavelet Transform

print("--- [enhancement.py - PDF Algorithm Implementation] Loading ---")

# ==========================================
# SHARED UTILS (Restored for App Compatibility)
# ==========================================

def _apply_hsv_brightening(image, brightening_factor=1.2):
    """
    Restored Helper: Applies a global brightening/darkening factor to the V channel.
    Required by app.py for the /brighten and /darken endpoints.
    """
    try:
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        H, S, V = cv2.split(hsv_image)
        
        # Apply factor
        V_float = V.astype(np.float32) * brightening_factor
        V_final = np.clip(V_float, 0, 255).astype(np.uint8)
        
        hsv_final = cv2.merge([H, S, V_final])
        final_image = cv2.cvtColor(hsv_final, cv2.COLOR_HSV2BGR)
        return final_image
    except Exception as e:
        print(f"Error in _apply_hsv_brightening: {e}")
        return image

def _normalize_to_8bit(img):
    """Helper to normalize float image to 0-255 uint8."""
    return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

def _apply_gamma(image, gamma=1.0):
    """Applies Gamma Correction."""
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)

# ==========================================
# PIPELINE A: Low Light (Mean > 5%)
# ==========================================
def run_pipeline_a(img):
    """
    Implementation of Pipeline A for images that are not 'ultra' dark.
    [cite_start]Steps: HSV -> CLAHE -> Final Polish [cite: 6-10]
    """
    print("... Executing Pipeline A (Standard Low Light) ...")
    
    # 1. Convert BGR to HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv) #
    
    # 2. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    v_enhanced = clahe.apply(v)
    
    # 3. Convert HSV to BGR
    hsv_merged = cv2.merge([h, s, v_enhanced])
    bgr_enhanced = cv2.cvtColor(hsv_merged, cv2.COLOR_HSV2BGR)
    
    # 4. Final Polish: Increase Brightness
    final_polish = cv2.convertScaleAbs(bgr_enhanced, alpha=1.1, beta=10)
    
    return final_polish

# ==========================================
# PIPELINE B: Ultra Dark (Mean < 5%)
# ==========================================

# --- Path 1: Multi-Scale Retinex with Color Restoration (MSRCR) ---
def _path_1_retinex(img):
    print("... ... Path 1: MSRCR (Local Contrast) ...")
    
    # 1. BGR to LAB, separate L channel
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # 2. Retinex (MSR) on L channel
    l_float = l_channel.astype(np.float64) + 1.0
    scales = [15, 80, 250]
    retinex_sum = np.zeros_like(l_float)
    
    for sigma in scales:
        blur = cv2.GaussianBlur(l_float, (0, 0), sigma)
        retinex_sum += (np.log10(l_float) - np.log10(blur))
        
    msr_result = retinex_sum / len(scales)
    msr_l = cv2.normalize(msr_result, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # 3. Color Restoration: High Gamma on original BGR
    color_restored_bgr = _apply_gamma(img, gamma=2.2) 
    lab_color_restored = cv2.cvtColor(color_restored_bgr, cv2.COLOR_BGR2LAB)
    _, a_new, b_new = cv2.split(lab_color_restored)
    
    # 4. Fusion
    merged_lab = cv2.merge([msr_l, a_new, b_new])
    output_path_1 = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)
    
    return output_path_1

# --- Path 2: Wavelet (Frequency Domain) ---
def _path_2_wavelet(img):
    print("... ... Path 2: Wavelet Transform (Frequency Domain) ...")
    
    # 1. BGR to HSV, separate Value channel
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    # 2. Wavelet Decomposition (DWT) -> LL, LH, HL, HH
    coeffs = pywt.dwt2(v, 'haar')
    LL, (LH, HL, HH) = coeffs
    
    # 3. Enhancement: CLAHE on LL Band
    LL_uint8 = _normalize_to_8bit(LL)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    LL_enhanced = clahe.apply(LL_uint8)
    
    # 4. Reconstruction (IDWT)
    coeffs_new = (LL_enhanced.astype(np.float64), (LH, HL, HH))
    v_reconstructed = pywt.idwt2(coeffs_new, 'haar')
    v_reconstructed = cv2.resize(v_reconstructed, (v.shape[1], v.shape[0]))
    v_final = v_reconstructed.astype(np.uint8)
    
    # Re-merge HSV
    hsv_new = cv2.merge([h, s, v_final])
    img_reconstructed = cv2.cvtColor(hsv_new, cv2.COLOR_HSV2BGR)
    
    # 5. Final Gamma Boost
    output_path_2 = _apply_gamma(img_reconstructed, gamma=1.2)
    
    return output_path_2

# --- Post-Processing & Fusion ---
def _fusion_and_polish(img_path1, img_path2):
    print("... ... Dual-Stream Fusion & Polish ...")
    
    # a) Dual-Stream Fusion
    fused = cv2.addWeighted(img_path1, 0.6, img_path2, 0.4, 0)
    
    # b) Denoising
    denoised = cv2.fastNlMeansDenoisingColored(fused, None, 10, 10, 7, 21)
    
    # c) Statistical Connection
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    l_float = l.astype(np.float32)
    current_mean = np.mean(l_float)
    current_std = np.std(l_float)
    
    target_mean = 120.0 
    target_std = 30.0   
    
    if current_std > 0:
        l_aligned = ((l_float - current_mean) / current_std) * target_std + target_mean
    else:
        l_aligned = l_float
        
    l_aligned = np.clip(l_aligned, 0, 255).astype(np.uint8)
    
    lab_aligned = cv2.merge([l_aligned, a, b])
    bgr_aligned = cv2.cvtColor(lab_aligned, cv2.COLOR_LAB2BGR)
    
    # Final Polish: Saturation Boost & Sharpening
    hsv_p = cv2.cvtColor(bgr_aligned, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv_p)
    s_boost = cv2.convertScaleAbs(s, alpha=1.3, beta=0) 
    hsv_polished = cv2.merge([h, s_boost, v])
    bgr_polished = cv2.cvtColor(hsv_polished, cv2.COLOR_HSV2BGR)
    
    kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
    final_output = cv2.filter2D(bgr_polished, -1, kernel)
    
    return final_output

def run_pipeline_b(img):
    """
    Implementation of Pipeline B for Ultra Dark Images.
    """
    # Path 1: MSRCR
    out_path1 = _path_1_retinex(img)
    # Path 2: Wavelet
    out_path2 = _path_2_wavelet(img)
    # Fusion
    final_output = _fusion_and_polish(out_path1, out_path2)
    
    return out_path1, out_path2, final_output

# ==========================================
# MAIN INTERFACE
# ==========================================
def get_all_enhancements(cv2_image: np.ndarray):
    """
    Main entry point. 
    """
    try:
        if cv2_image is None:
            raise ValueError("Input cv2_image is None")
            
        # 1. Convert BGR to LAB
        lab_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2LAB)
        l_channel, _, _ = cv2.split(lab_image)
        
        # 2. Calculate Mean Brightness
        mean_brightness = np.mean(l_channel)
        mean_brightness_percent = (mean_brightness / 255) * 100
        print(f"--- Mean Brightness: {mean_brightness:.2f}% ---")
        
        # 3. Pipeline Decision
        threshold = 5.0
        
        if mean_brightness_percent > threshold:
            # Pipeline A (Mean > 5%)
            pipeline_selected = "A"
            final_img = run_pipeline_a(cv2_image)
            return final_img, final_img, final_img, pipeline_selected
        else:
            # Pipeline B (Mean < 5%)
            # Visualize Steps: 1x=Path1, 2x=Path2, 3x=Final Fused
            pipeline_selected = "B"
            path1, path2, final_img = run_pipeline_b(cv2_image)
            return path1, path2, final_img, pipeline_selected

    except Exception as e:
        print(f"!!! Error in enhancement pipeline: {e}")
        traceback.print_exc()
        return cv2_image, cv2_image, cv2_image, "Error"