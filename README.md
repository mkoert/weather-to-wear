# API Data Visualization Project

This project is a web application that retrieves hourly weather data from a specified API and displays it using a visually appealing D3.js chart. The application is built using Flask for the backend and D3.js for the frontend visualization.

## Project Structure

```
weather
├── src
│   ├── main.py          # Entry point of the application
│   ├── api
│   │   └── client.py    # API client for fetching weather data
│   └── utils
│       └── data_processor.py  # Data processing utilities
├── static
│   ├── index.html       # Main HTML file for the web application
│   ├── css
│   │   └── style.css     # Styles for the web application (dev)
|   |   └── output.css     # Generated Styles for the web application (prod)
│   └── js
│       └── chart.js      # JavaScript for D3.js chart rendering
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd api-data-viz
   ```

2. **Install the required dependencies:**
   ```
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```
   python src/main.py
   ```

4. **Access the application:**
   Open your web browser and go to `http://127.0.0.1:5001` to view the D3.js chart displaying the hourly weather data.

## Usage

- The application fetches weather data from the specified API and processes it to extract hourly information.
- The processed data is then visualized using D3.js in the frontend.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License.



# https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/grand%20rapids%20mi?unitGroup=us&include=days%2Chours%2Calerts%2Ccurrent&key=PWUV4TLM3MAN62KW7JRUQX74M&contentType=json
# weather.michaelkoert.com
