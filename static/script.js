// --- 0. Global Settings ---
const MAX_DISPLAY_HEIGHT = 450; // Max height for canvas previews

// --- 1. Get All DOM Elements ---
const imageUploader = document.getElementById('imageUploader');
const enhanceButton = document.getElementById('enhanceButton');
const buttonText = document.getElementById('button-text');
const buttonSpinner = document.getElementById('button-spinner');

// Main View/Loading Elements
const loadingSpinner = document.getElementById('loading-spinner');
const viewerArea = document.getElementById('viewer-area');

// Original Image Elements
const originalCanvas = document.getElementById('originalCanvas');
const originalCtx = originalCanvas.getContext('2d');
const originalMessage = document.getElementById('originalMessage');

// Enhanced Image Elements (Now a single display)
const enhancedCanvas = document.getElementById('enhancedCanvas');
const enhancedCtx = enhancedCanvas.getContext('2d');
const enhancedMessage = document.getElementById('enhancedMessage');
const enhancedTitle = document.getElementById('enhanced-title');

// Output Selector
const outputSelector = document.getElementById('output-selector');
const btn1x = document.getElementById('btn-1x');
const btn2x = document.getElementById('btn-2x');
const btn3x = document.getElementById('btn-3x');
const outputButtons = [btn1x, btn2x, btn3x];

// --- MODIFIED: Brightness Elements ---
const brightnessControls = document.getElementById('brightness-controls');
const btnBrighten = document.getElementById('btn-brighten');
const btnDarken = document.getElementById('btn-darken'); // NEW

// Modal Elements
const modal = document.getElementById('modal');
const modalImage = document.getElementById('modalImage');
const closeModal = document.getElementById('closeModal');

// --- 2. Global State ---
let originalImage = null; // Holds the full-res original Image() object
let enhancedImages = {
    '1x': null, // Will hold base64 string
    '2x': null,
    '3x': null
};
let activeEnhancedView = '1x'; // Tracks which view is active ('1x', '2x', '3x')
let pipeline = 'B'; // Default to 'B' (Pipeline B)


// --- 3. Load and display the original image ---
imageUploader.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
        originalImage = new Image();
        originalImage.onload = () => {
            // Draw original image to its canvas
            drawToCanvas(originalCanvas, originalCtx, originalImage);
            originalMessage.style.display = 'none';
            originalCanvas.classList.add('ready');

            // Reset the enhanced side
            clearEnhancedDisplay();
            viewerArea.classList.remove('hidden'); // Show the viewer
            outputSelector.classList.add('hidden'); // Hide buttons
            brightnessControls.classList.add('hidden'); // Hide brightness controls
            loadingSpinner.classList.add('hidden'); // Hide spinner

            enhanceButton.disabled = false;
        };
        originalImage.src = event.target.result;
    };
    reader.readAsDataURL(file);
});


// --- 4. Enhance image by calling the Python API (MODIFIED) ---
enhanceButton.addEventListener('click', async () => {
    if (!originalImage) return;

    // --- Set loading state ---
    setLoadingState(true);

    try {
        // Send the *full original* image data
        const imageData = originalImage.src; 

        const response = await fetch('/enhance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: imageData }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Check for all 4 new items
        if (data.enhanced_1x && data.enhanced_2x && data.enhanced_3x && data.pipeline) {
            // Store all 3 results
            enhancedImages['1x'] = data.enhanced_1x;
            enhancedImages['2x'] = data.enhanced_2x;
            enhancedImages['3x'] = data.enhanced_3x;
            
            // Store the pipeline flag
            pipeline = data.pipeline;
            
            // Show the standard output selector
            outputSelector.classList.remove('hidden');

            // If Pipeline A, show the *new* brightness buttons
            if (pipeline === 'A') {
                brightnessControls.classList.remove('hidden');
            } else {
                brightnessControls.classList.add('hidden');
            }

            // Display the default (1x) image
            displayEnhancedImage('1x');

        } else {
            throw new Error("Invalid response from server. Missing images or pipeline flag.");
        }

    } catch (error) {
        console.error('Error enhancing image:', error);
        enhancedMessage.textContent = "An error occurred during enhancement.";
        enhancedMessage.style.display = 'block';
    } finally {
        // --- Reset loading state ---
        setLoadingState(false);
    }
});


// --- 5. Helper Functions (MODIFIED) ---

/**
 * Draws a given Image object onto a canvas, scaling it to MAX_DISPLAY_HEIGHT
 */
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

/**
 * Clears the enhanced image canvas and resets its message
 */
function clearEnhancedDisplay() {
    enhancedCtx.clearRect(0, 0, enhancedCanvas.width, enhancedCanvas.height);
    enhancedCanvas.width = 0;
    enhancedCanvas.height = 0;
    enhancedCanvas.classList.remove('ready');
    enhancedMessage.textContent = "Enhanced image will appear here";
    enhancedMessage.style.display = 'block';
    enhancedTitle.textContent = "Enhanced";
    enhancedImages = { '1x': null, '2x': null, '3x': null };
}

/**
 * Manages the UI during processing
 */
function setLoadingState(isLoading) {
    if (isLoading) {
        enhanceButton.disabled = true;
        buttonText.textContent = "Enhancing...";
        buttonSpinner.classList.remove('hidden');
        viewerArea.classList.add('hidden'); // Hide viewer
        loadingSpinner.classList.remove('hidden'); // Show spinner
        outputSelector.classList.add('hidden'); // Hide buttons
        brightnessControls.classList.add('hidden'); // Hide brightness controls
        clearEnhancedDisplay(); // Clear old results
    } else {
        enhanceButton.disabled = false;
        buttonText.textContent = "Enhance Image";
        buttonSpinner.classList.add('hidden');
        viewerArea.classList.remove('hidden'); // Show viewer
        loadingSpinner.classList.add('hidden'); // Hide spinner
    }
}

/**
 * Loads and displays one of the 3 enhanced images
 */
function displayEnhancedImage(level) { // level is '1x', '2x', or '3x'
    if (!enhancedImages[level]) return; // No image data

    activeEnhancedView = level;

    const enhancedImage = new Image();
    enhancedImage.onload = () => {
        drawToCanvas(enhancedCanvas, enhancedCtx, enhancedImage);
        enhancedMessage.style.display = 'none';
        enhancedCanvas.classList.add('ready');
    };
    enhancedImage.src = enhancedImages[level]; // Use stored base64 string

    // Update title
    let passText = level === '1x' ? 'Pass' : 'Passes';
    enhancedTitle.textContent = `Enhanced (${level} ${passText})`;
    
    // Update active button state
    outputButtons.forEach(btn => {
        btn.classList.toggle('active', btn.id === `btn-${level}`);
    });

    // --- MODIFIED LOGIC ---
    // Enable/disable the brightness buttons
    // They are only active if we are on '1x' and pipeline was 'A'
    const isBrightenActive = (level === '1x' && pipeline === 'A');
    btnBrighten.disabled = !isBrightenActive;
    btnDarken.disabled = !isBrightenActive; 

    // Special title for 1x pass in pipeline A
    if (isBrightenActive) {
        enhancedTitle.textContent = `Enhanced (1x Pass)`;
    }
}

// --- 6. Event Listeners for Output Buttons ---
btn1x.addEventListener('click', () => displayEnhancedImage('1x'));
btn2x.addEventListener('click', () => displayEnhancedImage('2x'));
btn3x.addEventListener('click', () => displayEnhancedImage('3x'));


// --- 7. MODIFIED: Event Listener for Brighten Button ---
btnBrighten.addEventListener('click', async () => {
    const currentImage = enhancedImages['1x'];
    if (!currentImage) return;

    // Set loading state for this button
    btnBrighten.disabled = true;
    btnDarken.disabled = true; // Disable both
    btnBrighten.textContent = "Applying...";
    enhancedMessage.textContent = "Applying +25% brightness...";
    enhancedMessage.style.display = 'block';
    enhancedCanvas.classList.remove('ready');

    try {
        const response = await fetch('/brighten', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: currentImage }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.brightened_image) {
            // SUCCESS! Overwrite the '1x' image with the new one
            enhancedImages['1x'] = data.brightened_image;
            // Re-display the 1x image
            displayEnhancedImage('1x'); 
            enhancedTitle.textContent = `Enhanced (1x Pass + Brightness)`;
        } else {
            throw new Error("Invalid response from /brighten");
        }

    } catch (error) {
        console.error('Error brightening image:', error);
        enhancedMessage.textContent = "An error occurred during brightening.";
    } finally {
        // Re-enable button
        btnBrighten.textContent = "Increase Brightness (+25%)";
        // Re-run display logic to set correct button states
        displayEnhancedImage(activeEnhancedView);
    }
});

// --- 8. NEW: Event Listener for Darken Button (CORRECTED) ---
btnDarken.addEventListener('click', async () => {
    const currentImage = enhancedImages['1x'];
    if (!currentImage) return;

    // Set loading state for this button
    btnBrighten.disabled = true; // Disable both
    btnDarken.disabled = true;
    btnDarken.textContent = "Applying...";
    enhancedMessage.textContent = "Applying -25% brightness...";
    enhancedMessage.style.display = 'block';
    enhancedCanvas.classList.remove('ready');

    try {
        const response = await fetch('/darken', { // Call new endpoint
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: currentImage }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // --- THIS IS THE CRITICAL LINE ---
        // Check for the "darkened_image" key from app.py
        if (data.darkened_image) { 
            // SUCCESS! Overwrite the '1x' image with the new one
            enhancedImages['1x'] = data.darkened_image;
            // Re-display the 1x image
            displayEnhancedImage('1x'); 
            enhancedTitle.textContent = `Enhanced (1x Pass - Brightness)`;
        } else {
            throw new Error("Invalid response from /darken");
        }

    } catch (error) {
        console.error('Error darkening image:', error);
        enhancedMessage.textContent = "An error occurred during darkening.";
    } finally {
        // Re-enable button
        btnDarken.textContent = "Decrease Brightness (-25%)";
        // Re-run display logic to set correct button states
        displayEnhancedImage(activeEnhancedView);
    }
});


// --- 9. Modal (Zoom) Logic ---
function openModal(canvas) {
    if (!canvas.classList.contains('ready')) return;

    let fullResSrc = '';
    if (canvas.id === 'originalCanvas') {
        fullResSrc = originalImage.src; // Use the stored full-res original
    } else if (canvas.id === 'enhancedCanvas') {
        // Use the stored full-res enhanced image based on the active view
        fullResSrc = enhancedImages[activeEnhancedView];
    }
    
    if (fullResSrc) {
        modalImage.src = fullResSrc;
        modal.classList.remove('hidden');
    }
}

// Add listeners to all canvases
originalCanvas.addEventListener('click', () => openModal(originalCanvas));
enhancedCanvas.addEventListener('click', () => openModal(enhancedCanvas));


function closeModalHandler() {
    modal.classList.add('hidden');
    modalImage.src = "";
}

closeModal.addEventListener('click', closeModalHandler);
modal.addEventListener('click', (e) => {
    if (e.target === modal) {
        closeModalHandler();
    }
});