const apiUrl = '/api/hourly-data';
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

async function fetchData(zipcode = null) {
    let url = apiUrl;
    if (zipcode) {
        url += `?zipcode=${encodeURIComponent(zipcode)}`;
    }
    const response = await fetch(url);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch weather data');
    }

    return data;
}

function showError(message) {
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('hidden');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorElement.classList.add('hidden');
        }, 5000);
    }
}

function hideError() {
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        errorElement.classList.add('hidden');
    }
}

function updateStats(data) {
    if (!data || data.length === 0) return;

    const firstHour = data[0];

    // Update temperature
    const tempElement = document.querySelector('[data-stat="temp"]');
    if (tempElement) {
        tempElement.textContent = Math.round(firstHour.temp || 0) + '°F';
    }

    // Update humidity
    const humidityElement = document.querySelector('[data-stat="humidity"]');
    if (humidityElement) {
        humidityElement.textContent = Math.round(firstHour.humidity || 0) + '%';
    }

    // Update wind speed
    const windElement = document.querySelector('[data-stat="wind"]');
    if (windElement) {
        windElement.textContent = Math.round(firstHour.windspeed || 0) + ' mph';
    }

    // Update conditions
    const conditionsElement = document.querySelector('[data-stat="conditions"]');
    if (conditionsElement) {
        conditionsElement.textContent = firstHour.conditions || '--';
    }
}

function showHourDetails(hourData) {
    const detailPanel = document.getElementById('hour-detail-panel');
    const detailContent = document.getElementById('hour-detail-content');
    const overlay = document.getElementById('overlay');

    if (!detailPanel || !detailContent) return;

    detailContent.innerHTML = `
        <div class="mb-4 pb-4 border-b border-gray-200">
            <h3 class="text-xl font-bold text-gray-800">Hour Details</h3>
            <p class="text-gray-600">${hourData.datetime}</p>
        </div>
        <div class="space-y-3">
            <div class="flex justify-between items-center">
                <span class="text-gray-600 font-medium">Temperature:</span>
                <span class="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-red-500">${Math.round(hourData.temp || 0)}°F</span>
            </div>
            <div class="flex justify-between items-center">
                <span class="text-gray-600 font-medium">Humidity:</span>
                <span class="text-xl font-semibold text-blue-600">${Math.round(hourData.humidity || 0)}%</span>
            </div>
            <div class="flex justify-between items-center">
                <span class="text-gray-600 font-medium">Wind Speed:</span>
                <span class="text-xl font-semibold text-green-600">${Math.round(hourData.windspeed || 0)} mph</span>
            </div>
            <div class="flex justify-between items-center">
                <span class="text-gray-600 font-medium">Precipitation:</span>
                <span class="text-xl font-semibold text-cyan-600">${hourData.precipitation || 0}%</span>
            </div>
            <div class="flex justify-between items-center">
                <span class="text-gray-600 font-medium">Snow:</span>
                <span class="text-xl font-semibold text-purple-600">${hourData.snow || 0}"</span>
            </div>
            <div class="flex justify-between items-center pt-2 border-t border-gray-200">
                <span class="text-gray-600 font-medium">Conditions:</span>
                <span class="text-lg font-semibold text-gray-700">${hourData.conditions || '--'}</span>
            </div>
        </div>
    `;

    if (overlay) {
        overlay.classList.remove('hidden');
    }
    detailPanel.classList.remove('hidden');
    detailPanel.classList.add('active');
}

function hideHourDetails() {
    const detailPanel = document.getElementById('hour-detail-panel');
    const overlay = document.getElementById('overlay');

    if (detailPanel) {
        detailPanel.classList.remove('active');
        setTimeout(() => {
            detailPanel.classList.add('hidden');
        }, 300);
    }

    if (overlay) {
        overlay.classList.add('hidden');
    }

    // Reset bar opacity
    d3.selectAll(".bar").attr("opacity", 1);
}

// Make hideHourDetails available globally for onclick handler
window.hideHourDetails = hideHourDetails;

function createChart(data) {
    const margin = { top: 20, right: 30, bottom: 40, left: 40 };
    const width = 800 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    const svg = d3.select("#chart")
        .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    const x = d3.scaleBand()
        .domain(data.map(d => d.datetime))
        .range([0, width])
        .padding(0.1);

    const y = d3.scaleLinear()
        .domain([0, d3.max(data, d => d.temp)])
        .nice()
        .range([height, 0]);

    svg.append("g")
        .selectAll(".bar")
        .data(data)
        .enter().append("rect")
        .attr("class", "bar")
        .attr("x", d => x(d.datetime))
        .attr("y", d => y(d.temp))
        .attr("width", x.bandwidth())
        .attr("height", d => height - y(d.temp))
        .attr("fill", "url(#barGradient)")
        .style("cursor", "pointer")
        .on("click", function(_, d) {
            // Remove highlight from all bars
            d3.selectAll(".bar").attr("opacity", 1);
            // Highlight the clicked bar
            d3.select(this).attr("opacity", 0.7);
            // Show the details
            showHourDetails(d);
        })
        .on("mouseenter", function() {
            d3.select(this).attr("opacity", 0.8);
        })
        .on("mouseleave", function() {
            d3.select(this).attr("opacity", 1);
        });

    // Add gradient definition
    svg.append("defs").append("linearGradient")
        .attr("id", "barGradient")
        .attr("x1", "0%")
        .attr("y1", "0%")
        .attr("x2", "0%")
        .attr("y2", "100%")
        .selectAll("stop")
        .data([
            { offset: "0%", color: "#f093fb" },
            { offset: "100%", color: "#4facfe" }
        ])
        .enter().append("stop")
        .attr("offset", d => d.offset)
        .attr("stop-color", d => d.color);

    svg.append("g")
        .attr("class", "x-axis")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(x));

    svg.append("g")
        .attr("class", "y-axis")
        .call(d3.axisLeft(y));
}

async function renderChart(zipcode = null) {
    try {
        // Clear existing chart
        d3.select("#chart").selectAll("*").remove();

        const data = await fetchData(zipcode);
        if (!data || data.length === 0) {
            console.error('No data available to render the chart.');
            showError('No weather data available for this location.');
            return;
        }
        if(data.length > 12) {
            data.splice(12); // Keep only the first 12 hours
        }
        hideError();
        updateStats(data);
        createChart(data);
    } catch (error) {
        console.error('Error rendering chart:', error);
        showError(error.message);
    }
}

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

function validateZipcode(zipcode) {
    // Basic US zipcode validation (5 digits or 5+4 format)
    const zipcodeRegex = /^\d{5}(-\d{4})?$/;
    return zipcodeRegex.test(zipcode);
}

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
        await renderChart(zipcode);
    } else {
        currentZipcode = null;
        saveZipcode(null);
        updateLocationDisplay(null);
        await renderChart();
    }
}

document.addEventListener("DOMContentLoaded", () => {
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

    // Initial render with saved zipcode or default location
    renderChart(currentZipcode);

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
});