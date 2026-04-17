const apiUrl = '/api/hourly-data';
const fashionApiUrl = '/api/fashion-suggestions';
const chatApiUrl = '/api/chat';
let currentWeatherData = null;
let currentZipcode = null;
let currentSuggestions = null;
let chatHistory = [];

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
        content.innerHTML = formatSuggestions(suggestions);
        container.classList.remove('hidden');
        container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    currentSuggestions = suggestions;
    openChat();
}

// Polar Wear Chat
const ACTIVITY_STARTERS = [
    'Going for a walk',
    'Running outside',
    'Commuting to work',
    'Outdoor errands',
    'Mostly indoors',
    'Something else',
];

function openChat() {
    const widget = document.getElementById('chat-widget');
    if (!widget) return;

    widget.classList.remove('hidden');

    if (chatHistory.length === 0) {
        renderChatMessage('assistant', "Hi, I'm Polar Wear! What are you doing today?");
        renderStarters(ACTIVITY_STARTERS);
    }

    // Panel stays closed; tease the user with an expanded pill after a beat.
    const toggle = document.getElementById('chat-toggle');
    if (toggle) {
        setTimeout(() => toggle.classList.add('expanded'), 600);
    }
}

function setChatPanelOpen(isOpen) {
    const panel = document.getElementById('chat-panel');
    const toggle = document.getElementById('chat-toggle');
    if (!panel || !toggle) return;
    panel.classList.toggle('hidden', !isOpen);
    toggle.classList.toggle('hidden', isOpen);
}

function renderStarters(options) {
    const startersEl = document.getElementById('chat-starters');
    if (!startersEl) return;

    startersEl.innerHTML = '';
    startersEl.classList.remove('hidden');

    options.forEach((text) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'chat-starter';
        btn.textContent = text;
        btn.addEventListener('click', () => sendChatMessage(text));
        startersEl.appendChild(btn);
    });
}

function renderChatMessage(role, text) {
    const messagesEl = document.getElementById('chat-messages');
    if (!messagesEl) return;

    const wrapper = document.createElement('div');
    wrapper.className = role === 'user' ? 'flex justify-end' : 'flex justify-start';

    const bubble = document.createElement('div');
    bubble.className = role === 'user'
        ? 'max-w-[80%] px-4 py-2 rounded-2xl bg-blue-500 text-white rounded-br-sm'
        : 'max-w-[80%] px-4 py-2 rounded-2xl bg-gray-100 text-gray-800 rounded-bl-sm';
    bubble.textContent = text;

    wrapper.appendChild(bubble);
    messagesEl.appendChild(wrapper);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setChatTyping(isTyping) {
    const existing = document.getElementById('chat-typing');
    if (isTyping && !existing) {
        const messagesEl = document.getElementById('chat-messages');
        const wrapper = document.createElement('div');
        wrapper.id = 'chat-typing';
        wrapper.className = 'flex justify-start';
        wrapper.innerHTML = '<div class="px-4 py-2 rounded-2xl bg-gray-100 text-gray-500 text-sm">Polar Wear is typing…</div>';
        messagesEl.appendChild(wrapper);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    } else if (!isTyping && existing) {
        existing.remove();
    }
}

async function sendChatMessage(text) {
    const trimmed = (text || '').trim();
    if (!trimmed) return;

    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');
    if (input) input.value = '';
    if (sendBtn) sendBtn.disabled = true;

    const startersEl = document.getElementById('chat-starters');
    if (startersEl && chatHistory.length === 0) startersEl.classList.add('hidden');

    chatHistory.push({ role: 'user', content: trimmed });
    renderChatMessage('user', trimmed);
    setChatTyping(true);

    try {
        const response = await fetch(chatApiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: chatHistory,
                weather: currentWeatherData ? currentWeatherData[0] : null,
                suggestions: currentSuggestions,
                zipcode: currentZipcode,
            }),
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Chat failed');
        }

        const reply = result.reply || '';
        chatHistory.push({ role: 'assistant', content: reply });
        renderChatMessage('assistant', reply);
    } catch (error) {
        console.error('Chat error:', error);
        renderChatMessage('assistant', `Sorry — ${error.message}`);
    } finally {
        setChatTyping(false);
        if (sendBtn) sendBtn.disabled = false;
        if (input) input.focus();
    }
}

// Format structured suggestions into cards
function formatSuggestions(data) {
    // Fallback for string responses
    if (typeof data === 'string') {
        return `<p class="text-gray-700">${data.replace(/\n/g, '<br>')}</p>`;
    }

    let html = '';

    // Summary
    if (data.summary) {
        html += `<p class="text-lg text-gray-700 mb-6 leading-relaxed">${data.summary}</p>`;
    }

    // Outfit items
    if (data.outfit && data.outfit.length > 0) {
        html += `<h4 class="text-sm font-bold uppercase tracking-wide text-gray-500 mb-3">Recommended Outfit</h4>`;
        html += `<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">`;
        for (const item of data.outfit) {
            html += `
                <div class="outfit-card flex items-start gap-3 p-4 bg-white rounded-xl border border-gray-100 shadow-sm">
                    <div class="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                        </svg>
                    </div>
                    <div class="min-w-0">
                        <p class="font-semibold text-gray-800">${item.item}</p>
                        <p class="text-sm text-gray-500">${item.description}</p>
                        <p class="text-xs text-blue-600 mt-1">${item.reason}</p>
                    </div>
                </div>`;
        }
        html += `</div>`;
    }

    // Accessories
    if (data.accessories && data.accessories.length > 0) {
        html += `<h4 class="text-sm font-bold uppercase tracking-wide text-gray-500 mb-3">Accessories</h4>`;
        html += `<div class="flex flex-wrap gap-2 mb-6">`;
        for (const acc of data.accessories) {
            html += `
                <span class="inline-flex items-center gap-2 px-4 py-2 bg-purple-50 text-purple-800 rounded-full text-sm border border-purple-100"
                      title="${acc.reason}">
                    ${acc.item}
                </span>`;
        }
        html += `</div>`;
    }

    // Tips
    if (data.tips && data.tips.length > 0) {
        html += `<h4 class="text-sm font-bold uppercase tracking-wide text-gray-500 mb-3">Comfort Tips</h4>`;
        html += `<ul class="space-y-2">`;
        for (const tip of data.tips) {
            html += `
                <li class="flex items-start gap-2 text-gray-700 text-sm">
                    <span class="text-green-500 mt-0.5 shrink-0">&#10003;</span>
                    ${tip}
                </li>`;
        }
        html += `</ul>`;
    }

    return html;
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

    // Chat form submit
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const input = document.getElementById('chat-input');
            sendChatMessage(input ? input.value : '');
        });
    }

    // Chat widget toggle / close
    const chatToggle = document.getElementById('chat-toggle');
    if (chatToggle) {
        chatToggle.addEventListener('click', () => setChatPanelOpen(true));
    }
    const chatClose = document.getElementById('chat-close');
    if (chatClose) {
        chatClose.addEventListener('click', () => setChatPanelOpen(false));
    }
});
