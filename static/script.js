const MAX_DISPLAY_HEIGHT = 450; 
const loadingSpinner = document.getElementById('loading-spinner');
const loadingText = document.getElementById('loading-text');

const tabImage = document.getElementById('tab-image');
const tabVideo = document.getElementById('tab-video');
const sectionImage = document.getElementById('section-image');
const sectionVideo = document.getElementById('section-video');

function switchTab(mode) {
    if (mode === 'image') {
        sectionImage.classList.remove('hidden');
        sectionVideo.classList.add('hidden');
        tabImage.classList.add('bg-indigo-600', 'text-white', 'shadow-sm');
        tabImage.classList.remove('text-gray-600', 'hover:bg-gray-100');
        tabVideo.classList.remove('bg-emerald-600', 'text-white', 'shadow-sm');
        tabVideo.classList.add('text-gray-600', 'hover:bg-gray-100');
    } else {
        sectionImage.classList.add('hidden');
        sectionVideo.classList.remove('hidden');
        tabVideo.classList.add('bg-emerald-600', 'text-white', 'shadow-sm');
        tabVideo.classList.remove('text-gray-600', 'hover:bg-gray-100');
        tabImage.classList.remove('bg-indigo-600', 'text-white', 'shadow-sm');
        tabImage.classList.add('text-gray-600', 'hover:bg-gray-100');
    }
}

tabImage.addEventListener('click', () => switchTab('image'));
tabVideo.addEventListener('click', () => switchTab('video'));

const imageUploader = document.getElementById('imageUploader');
const enhanceButton = document.getElementById('enhanceButton');
const buttonText = document.getElementById('button-text');
const buttonSpinner = document.getElementById('button-spinner');

const originalCanvas = document.getElementById('originalCanvas');
const originalCtx = originalCanvas.getContext('2d');
const originalMessage = document.getElementById('originalMessage');

const enhancedCanvas = document.getElementById('enhancedCanvas');
const enhancedCtx = enhancedCanvas.getContext('2d');
const enhancedMessage = document.getElementById('enhancedMessage');
const enhancedTitle = document.getElementById('enhanced-title');

const outputSelector = document.getElementById('output-selector');
const brightnessControls = document.getElementById('brightness-controls');
const btn1x = document.getElementById('btn-1x');
const btn2x = document.getElementById('btn-2x');
const btn3x = document.getElementById('btn-3x');
const btnBrighten = document.getElementById('btn-brighten');
const btnDarken = document.getElementById('btn-darken');
const outputButtons = [btn1x, btn2x, btn3x];

let originalImage = null;
let enhancedImages = { '1x': null, '2x': null, '3x': null };
let activeEnhancedView = '1x';
let pipeline = 'B'; 

imageUploader.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
        originalImage = new Image();
        originalImage.onload = () => {
            drawToCanvas(originalCanvas, originalCtx, originalImage);
            originalMessage.style.display = 'none';
            originalCanvas.classList.add('ready');

            clearEnhancedDisplay();
            document.getElementById('viewer-area').classList.remove('hidden');
            outputSelector.classList.add('hidden');
            brightnessControls.classList.add('hidden');
            loadingSpinner.classList.add('hidden');

            enhanceButton.disabled = false;
        };
        originalImage.src = event.target.result;
    };
    reader.readAsDataURL(file);
});

enhanceButton.addEventListener('click', async () => {
    if (!originalImage) return;
    setImageLoadingState(true);

    try {
        const response = await fetch('/enhance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: originalImage.src }),
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();

        if (data.enhanced_1x && data.pipeline) {
            enhancedImages['1x'] = data.enhanced_1x;
            enhancedImages['2x'] = data.enhanced_2x;
            enhancedImages['3x'] = data.enhanced_3x;
            pipeline = data.pipeline;
            
            outputSelector.classList.remove('hidden');
            
            if (pipeline === 'A') {
                brightnessControls.classList.remove('hidden');
            } else {
                brightnessControls.classList.add('hidden');
            }

            displayEnhancedImage('1x');
        } else {
            throw new Error("Invalid response.");
        }
    } catch (error) {
        console.error(error);
        enhancedMessage.textContent = "Error during enhancement.";
        enhancedMessage.style.display = 'block';
    } finally {
        setImageLoadingState(false);
    }
});

function drawToCanvas(canvas, ctx, image) {
    let { width, height } = image;
    if (height > MAX_DISPLAY_HEIGHT) {
        const scale = MAX_DISPLAY_HEIGHT / height;
        height = MAX_DISPLAY_HEIGHT;
        width = width * scale;
    }
    canvas.width = width;
    canvas.height = height;
    ctx.drawImage(image, 0, 0, width, height);
}

function clearEnhancedDisplay() {
    enhancedCtx.clearRect(0, 0, enhancedCanvas.width, enhancedCanvas.height);
    enhancedCanvas.width = 0;
    enhancedCanvas.height = 0;
    enhancedCanvas.classList.remove('ready');
    enhancedMessage.textContent = "Enhanced image will appear here";
    enhancedMessage.style.display = 'block';
    enhancedImages = { '1x': null, '2x': null, '3x': null };
}

function setImageLoadingState(isLoading) {
    if (isLoading) {
        enhanceButton.disabled = true;
        buttonText.textContent = "Enhancing...";
        buttonSpinner.classList.remove('hidden');
        document.getElementById('viewer-area').classList.add('hidden');
        loadingSpinner.classList.remove('hidden');
        loadingText.textContent = "Enhancing image, please wait...";
        outputSelector.classList.add('hidden');
        brightnessControls.classList.add('hidden');
    } else {
        enhanceButton.disabled = false;
        buttonText.textContent = "Enhance Image";
        buttonSpinner.classList.add('hidden');
        document.getElementById('viewer-area').classList.remove('hidden');
        loadingSpinner.classList.add('hidden');
    }
}

function displayEnhancedImage(level) {
    if (!enhancedImages[level]) return;
    activeEnhancedView = level;

    const img = new Image();
    img.onload = () => {
        drawToCanvas(enhancedCanvas, enhancedCtx, img);
        enhancedMessage.style.display = 'none';
        enhancedCanvas.classList.add('ready');
    };
    img.src = enhancedImages[level];

    let passText = level === '1x' ? 'Pass' : 'Passes';
    enhancedTitle.textContent = `Enhanced (${level} ${passText})`;
    if (level === '1x' && pipeline === 'A') enhancedTitle.textContent = "Enhanced (1x Pass)";

    outputButtons.forEach(btn => btn.classList.toggle('active', btn.id === `btn-${level}`));
    
    const isBrightenActive = (level === '1x' && pipeline === 'A');
    btnBrighten.disabled = !isBrightenActive;
    btnDarken.disabled = !isBrightenActive;
}

btn1x.addEventListener('click', () => displayEnhancedImage('1x'));
btn2x.addEventListener('click', () => displayEnhancedImage('2x'));
btn3x.addEventListener('click', () => displayEnhancedImage('3x'));

async function applyBrightness(factorType) {
    const currentImage = enhancedImages['1x'];
    if (!currentImage) return;

    btnBrighten.disabled = true;
    btnDarken.disabled = true;
    enhancedMessage.textContent = "Adjusting brightness...";
    enhancedMessage.style.display = 'block';
    enhancedCanvas.classList.remove('ready');

    const endpoint = factorType === 'brighten' ? '/brighten' : '/darken';
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: currentImage }),
        });

        if (!response.ok) throw new Error("Error adjusting brightness");
        const data = await response.json();

        const newImg = factorType === 'brighten' ? data.brightened_image : data.darkened_image;
        
        if (newImg) {
            enhancedImages['1x'] = newImg;
            displayEnhancedImage('1x');
            const sign = factorType === 'brighten' ? '+' : '-';
            enhancedTitle.textContent = `Enhanced (1x Pass ${sign} Brightness)`;
        }
    } catch (error) {
        console.error(error);
    } finally {
        displayEnhancedImage('1x');
    }
}

btnBrighten.addEventListener('click', () => applyBrightness('brighten'));
btnDarken.addEventListener('click', () => applyBrightness('darken'));

const videoUploader = document.getElementById('videoUploader');
const enhanceVideoButton = document.getElementById('enhanceVideoButton');
const videoResultArea = document.getElementById('video-result-area');
const resultVideo = document.getElementById('resultVideo');
const downloadVideoLink = document.getElementById('downloadVideoLink');
let currentVideoFile = null;

videoUploader.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        currentVideoFile = e.target.files[0];
        enhanceVideoButton.disabled = false;
    }
});

enhanceVideoButton.addEventListener('click', async () => {
    if (!currentVideoFile) return;

    enhanceVideoButton.disabled = true;
    enhanceVideoButton.textContent = "Processing...";
    videoResultArea.classList.add('hidden');
    sectionVideo.classList.add('hidden');
    loadingSpinner.classList.remove('hidden');
    loadingText.textContent = "Processing Video (Smart Sampling)... This may take a while.";

    try {
        const formData = new FormData();
        formData.append('file', currentVideoFile);

        const response = await fetch('/enhance-video', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Video processing failed");
        const data = await response.json();
        
        if (data.video_url) {
            resultVideo.src = data.video_url;
            downloadVideoLink.href = data.video_url;
            videoResultArea.classList.remove('hidden');
        }

    } catch (error) {
        console.error(error);
        alert("Error processing video. Check console.");
    } finally {
        loadingSpinner.classList.add('hidden');
        sectionVideo.classList.remove('hidden');
        enhanceVideoButton.disabled = false;
        enhanceVideoButton.textContent = "Process Video";
    }
});

const modal = document.getElementById('modal');
const modalImage = document.getElementById('modalImage');
const closeModal = document.getElementById('closeModal');

function openModal(canvas) {
    if (!canvas.classList.contains('ready')) return;
    let src = '';
    if (canvas.id === 'originalCanvas') src = originalImage.src;
    else if (canvas.id === 'enhancedCanvas') src = enhancedImages[activeEnhancedView];
    
    if (src) {
        modalImage.src = src;
        modal.classList.remove('hidden');
    }
}

originalCanvas.addEventListener('click', () => openModal(originalCanvas));
enhancedCanvas.addEventListener('click', () => openModal(enhancedCanvas));

closeModal.addEventListener('click', () => modal.classList.add('hidden'));
modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
});