import cv2
import numpy as np
import traceback
import pywt

def _apply_hsv_brightening(image, brightening_factor=1.2):
    try:
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        H, S, V = cv2.split(hsv_image) 
        
        V_float = V.astype(np.float32) * brightening_factor
        V_final = np.clip(V_float, 0, 255).astype(np.uint8)
        
        hsv_final = cv2.merge([H, S, V_final])
        final_image = cv2.cvtColor(hsv_final, cv2.COLOR_HSV2BGR)
        return final_image
    except Exception as e:
        print(f"Error in _apply_hsv_brightening: {e}")
        return image

def _normalize_to_8bit(img):
    return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

def _apply_gamma(image, gamma=1.0):
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)

def run_pipeline_a(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    v_enhanced = clahe.apply(v)
    
    hsv_merged = cv2.merge([h, s, v_enhanced])
    bgr_enhanced = cv2.cvtColor(hsv_merged, cv2.COLOR_HSV2BGR)
    
    final_polish = cv2.convertScaleAbs(bgr_enhanced, alpha=1.1, beta=10)
    
    return final_polish

def _path_1_retinex(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    l_float = l_channel.astype(np.float64) + 1.0
    scales = [15, 80, 250]
    retinex_sum = np.zeros_like(l_float)
    
    for sigma in scales:
        blur = cv2.GaussianBlur(l_float, (0, 0), sigma)
        retinex_sum += (np.log10(l_float) - np.log10(blur))
        
    msr_result = retinex_sum / len(scales)
    msr_l = cv2.normalize(msr_result, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    color_restored_bgr = _apply_gamma(img, gamma=2.2) 
    lab_color_restored = cv2.cvtColor(color_restored_bgr, cv2.COLOR_BGR2LAB)
    _, a_new, b_new = cv2.split(lab_color_restored)
    
    merged_lab = cv2.merge([msr_l, a_new, b_new])
    output_path_1 = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)
    
    return output_path_1

def _path_2_wavelet(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    coeffs = pywt.dwt2(v, 'haar') 
    LL, (LH, HL, HH) = coeffs
    
    LL_uint8 = _normalize_to_8bit(LL)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    LL_enhanced = clahe.apply(LL_uint8)
    
    coeffs_new = (LL_enhanced.astype(np.float64), (LH, HL, HH))
    v_reconstructed = pywt.idwt2(coeffs_new, 'haar')
    v_reconstructed = cv2.resize(v_reconstructed, (v.shape[1], v.shape[0]))
    v_final = v_reconstructed.astype(np.uint8)
    
    hsv_new = cv2.merge([h, s, v_final])
    img_reconstructed = cv2.cvtColor(hsv_new, cv2.COLOR_HSV2BGR)
    
    output_path_2 = _apply_gamma(img_reconstructed, gamma=1.2)
    
    return output_path_2

def _fusion_and_polish(img_path1, img_path2):
    fused = cv2.addWeighted(img_path1, 0.6, img_path2, 0.4, 0)
    
    denoised = cv2.fastNlMeansDenoisingColored(fused, None, 10, 10, 7, 21)
    
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
    
    hsv_p = cv2.cvtColor(bgr_aligned, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv_p)
    s_boost = cv2.convertScaleAbs(s, alpha=1.3, beta=0) 
    hsv_polished = cv2.merge([h, s_boost, v])
    bgr_polished = cv2.cvtColor(hsv_polished, cv2.COLOR_HSV2BGR)
    
    kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
    final_output = cv2.filter2D(bgr_polished, -1, kernel)
    
    return final_output

def run_pipeline_b(img):
    out_path1 = _path_1_retinex(img)
    out_path2 = _path_2_wavelet(img)
    final_output = _fusion_and_polish(out_path1, out_path2)
    
    return out_path1, out_path2, final_output

def get_all_enhancements(cv2_image: np.ndarray):
    try:
        if cv2_image is None:
            raise ValueError("Input cv2_image is None")
            
        lab_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2LAB)
        l_channel, _, _ = cv2.split(lab_image)
        
        mean_brightness = np.mean(l_channel)
        mean_brightness_percent = (mean_brightness / 255) * 100
        print(f"--- Mean Brightness: {mean_brightness:.2f}% ---")
        
        threshold = 5.0
        
        if mean_brightness_percent > threshold:
            pipeline_selected = "A"
            final_img = run_pipeline_a(cv2_image)
            return final_img, final_img, final_img, pipeline_selected
        else:
            pipeline_selected = "B"
            path1, path2, final_img = run_pipeline_b(cv2_image)
            return path1, path2, final_img, pipeline_selected

    except Exception as e:
        print(f"!!! Error in enhancement pipeline: {e}")
        traceback.print_exc()
        return cv2_image, cv2_image, cv2_image, "Error"