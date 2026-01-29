const apiUrl = '/api/hourly-data';
const fashionApiUrl = '/api/fashion-suggestions';
let currentWeatherData = null;
let currentZipcode = null;

// Get zipcode from localStorage
function getSavedZipcode() {
    return localStorage.getItem('userZipcode');
}

// Save zipcode to localStorage
function saveZipcode(zipcode) {
    if (zipcode) {
        localStorage.setItem('userZipcode', zipcode);
    } else {
        localStorage.removeItem('userZipcode');
    }
}

// Validate zipcode format
function validateZipcode(zipcode) {
    const zipcodeRegex = /^\d{5}(-\d{4})?$/;
    return zipcodeRegex.test(zipcode);
}

// Update location display
function updateLocationDisplay(zipcode) {
    const locationDisplay = document.getElementById('location-display');
    if (locationDisplay) {
        if (zipcode) {
            locationDisplay.textContent = `Zipcode: ${zipcode}`;
        } else {
            locationDisplay.textContent = 'Grand Rapids, MI';
        }
    }
}

// Fetch current weather data
async function fetchWeatherData(zipcode = null) {
    try {
        let url = apiUrl;
        if (zipcode) {
            url += `?zipcode=${encodeURIComponent(zipcode)}`;
        }
        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch weather data');
        }

        currentWeatherData = data;
        updateWeatherDisplay(data);
        return data;
    } catch (error) {
        console.error('Error fetching weather data:', error);
        showError(error.message);
        return null;
    }
}

// Update weather display
function updateWeatherDisplay(data) {
    if (!data || data.length === 0) return;

    const firstHour = data[0];
    const recommendationElement = document.querySelector('[data-stat="clothing-recommendation"]');

    if (recommendationElement) {
        // Show a simple recommendation based on temperature
        const temp = firstHour.temp || 0;
        let recommendation = '--';

        if (temp < 32) {
            recommendation = 'Heavy winter coat, warm layers';
        } else if (temp < 50) {
            recommendation = 'Jacket or sweater';
        } else if (temp < 70) {
            recommendation = 'Light jacket or long sleeves';
        } else if (temp < 85) {
            recommendation = 'T-shirt and shorts/pants';
        } else {
            recommendation = 'Light, breathable clothing';
        }

        recommendationElement.textContent = recommendation;
    }
}

// Show error message
function showError(message) {
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('hidden');

        setTimeout(() => {
            errorElement.classList.add('hidden');
        }, 5000);
    }
}

// Handle file input change
function handleFileSelect(event) {
    const file = event.target.files[0];
    const previewContainer = document.getElementById('upload-preview');
    const previewImage = document.getElementById('preview-image');
    const placeholder = document.getElementById('upload-placeholder');
    const submitBtn = document.getElementById('get-suggestions-btn');

    if (file) {
        // Show preview
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            previewContainer.classList.remove('hidden');
            placeholder.classList.add('hidden');
            submitBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    } else {
        // Hide preview
        previewContainer.classList.add('hidden');
        placeholder.classList.remove('hidden');
        submitBtn.disabled = true;
    }
}

// Handle form submission
async function handleFormSubmit(event) {
    event.preventDefault();

    const fileInput = document.getElementById('closet-image');
    const file = fileInput.files[0];

    if (!file) {
        showError('Please select an image first');
        return;
    }

    if (!currentWeatherData || currentWeatherData.length === 0) {
        showError('Weather data not available. Please refresh the page.');
        return;
    }

    // Show loading
    const loadingMessage = document.getElementById('loading-message');
    const submitBtn = document.getElementById('get-suggestions-btn');
    loadingMessage.classList.remove('hidden');
    submitBtn.disabled = true;

    // Prepare form data
    const formData = new FormData();
    formData.append('image', file);
    formData.append('weather_data', JSON.stringify(currentWeatherData[0]));

    try {
        const response = await fetch(fashionApiUrl, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Failed to get fashion suggestions');
        }

        // Display suggestions
        displaySuggestions(result.suggestions);
    } catch (error) {
        console.error('Error getting fashion suggestions:', error);
        showError(error.message);
    } finally {
        // Hide loading
        loadingMessage.classList.add('hidden');
        submitBtn.disabled = false;
    }
}

// Display fashion suggestions
function displaySuggestions(suggestions) {
    const container = document.getElementById('suggestions-container');
    const content = document.getElementById('suggestions-content');

    if (container && content) {
        // Format the suggestions (assuming it's markdown or plain text from Claude)
        content.innerHTML = formatSuggestions(suggestions);
        container.classList.remove('hidden');

        // Scroll to suggestions
        container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Format suggestions text
function formatSuggestions(text) {
    // Convert line breaks to HTML
    const formatted = text
        .split('\n')
        .map(line => {
            // Bold text for headers (lines ending with :)
            if (line.trim().endsWith(':')) {
                return `<h4 class="font-bold text-lg mt-4 mb-2 text-gray-800">${line}</h4>`;
            }
            // Bullet points
            if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
                return `<li class="ml-4 text-gray-700">${line.substring(1).trim()}</li>`;
            }
            // Regular paragraphs
            if (line.trim()) {
                return `<p class="text-gray-700 mb-2">${line}</p>`;
            }
            return '';
        })
        .join('');

    return formatted;
}

// Handle search button click
async function handleSearch() {
    const zipcodeInput = document.getElementById('zipcode-input');
    const zipcode = zipcodeInput.value.trim();

    if (zipcode) {
        // Validate zipcode format
        if (!validateZipcode(zipcode)) {
            showError('Please enter a valid 5-digit US zipcode.');
            return;
        }

        currentZipcode = zipcode;
        saveZipcode(zipcode);
        updateLocationDisplay(zipcode);
        await fetchWeatherData(zipcode);
    } else {
        currentZipcode = null;
        saveZipcode(null);
        updateLocationDisplay(null);
        await fetchWeatherData();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Load saved zipcode from localStorage
    const savedZipcode = getSavedZipcode();
    if (savedZipcode) {
        currentZipcode = savedZipcode;
        const zipcodeInput = document.getElementById('zipcode-input');
        if (zipcodeInput) {
            zipcodeInput.value = savedZipcode;
        }
        updateLocationDisplay(savedZipcode);
    }

    // Fetch initial weather data with saved zipcode
    fetchWeatherData(currentZipcode);

    // Set up search button click handler
    const searchBtn = document.getElementById('search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', handleSearch);
    }

    // Set up Enter key handler for zipcode input
    const zipcodeInput = document.getElementById('zipcode-input');
    if (zipcodeInput) {
        zipcodeInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleSearch();
            }
        });
    }

    // Set up file input handler
    const fileInput = document.getElementById('closet-image');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }

    // Set up form submit handler
    const form = document.getElementById('closet-upload-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }

    // Disable submit button initially
    const submitBtn = document.getElementById('get-suggestions-btn');
    if (submitBtn) {
        submitBtn.disabled = true;
    }
});
