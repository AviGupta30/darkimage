import cv2
import numpy as np
import os
from enhancement import run_pipeline_a, run_pipeline_b

def _enhance_frame(frame, pipeline_type):
    if pipeline_type == "A":
        return run_pipeline_a(frame)
    else:
        _, _, final = run_pipeline_b(frame)
        return final

def process_video_smartly(input_path, output_path, sample_rate=4):
    print(f"--- Starting Smart Video Enhancement (Sample Rate: {sample_rate}) ---")
    
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError("Could not open video file.")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Original: {width}x{height} @ {fps}fps ({total_frames} frames)")

    ret, first_frame = cap.read()
    if not ret:
        raise ValueError("Video is empty.")
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    lab = cv2.cvtColor(first_frame, cv2.COLOR_BGR2LAB)
    l, _, _ = cv2.split(lab)
    mean_brightness = np.mean(l)
    mean_percent = (mean_brightness / 255) * 100
    
    pipeline_type = "A" if mean_percent > 5.0 else "B"
    print(f"--- Detected Brightness: {mean_percent:.2f}% -> Using Pipeline {pipeline_type} ---")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    prev_enhanced_frame = None
    frame_buffer = []
    
    processed_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        current_frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        
        if processed_count % sample_rate == 0:
            print(f"Processing Keyframe {processed_count}/{total_frames}...")
            curr_enhanced_frame = _enhance_frame(frame, pipeline_type)
            
            if prev_enhanced_frame is not None:
                for i in range(1, sample_rate):
                    alpha = i / sample_rate
                    interpolated = cv2.addWeighted(prev_enhanced_frame, 1 - alpha, curr_enhanced_frame, alpha, 0)
                    out.write(interpolated)
            
            out.write(curr_enhanced_frame)
            
            prev_enhanced_frame = curr_enhanced_frame
            
        processed_count += 1

    remaining = total_frames - processed_count
    
    cap.release()
    out.release()
    print("--- Video Enhancement Complete ---")
    return output_path