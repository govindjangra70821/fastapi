# FastAPI Shipping Recommendation Service

This FastAPI project provides an API for recommending shipping carriers based on coverage, attributes, weight range, and return requirements.

## Table of Contents
- [Installation](#installation)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Running the Server](#running-the-server)
- [API Usage](#api-usage)
  - [Health Check](#health-check)
  - [Process Shipping Requirements](#process-shipping-requirements)
- [Testing the API](#testing-the-api)

## Installation

To get started with the FastAPI server, follow these steps to set up your local development environment.

### Clone the Repository

```bash
git clone https://github.com/yourusername/shipping-recommendation-service.git
cd shipping-recommendation-service
```

### Setup Virtual Environment

It is recommended to use a virtual environment to manage dependencies. You can set up a virtual environment using `venv`.

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### Install Dependencies

With the virtual environment activated, install the required dependencies using `pip`.

```bash
pip install -r requirements.txt
```

### Environment Variables

This project requires certain environment variables to function correctly. Create a `.env` file in the root directory and add the following:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Replace `your_openai_api_key_here` with your actual OpenAI API key.

## Running the Server

Once the dependencies are installed and the environment variables are set, you can start the FastAPI server.

```bash
uvicorn main:app --reload
```

This command will start the server on `http://127.0.0.1:8000/`.

## API Usage

### Health Check

**Endpoint**: `GET /`

**Description**: A simple health check endpoint to ensure that the server is running.

**Response**:
```json
{
  "status": "ok"
}
```

### Process Shipping Requirements

**Endpoint**: `POST /process-shipping/`

**Description**: This endpoint processes shipping requirements and returns recommendations based on various criteria like coverage, attributes, weight range, and return needs.

**Request Body**:
```json
{
  "coverage_area": ["new york", "California"],
  "carrier_attributes": {
    "tracking": "none",
    "sustainability": "high",
    "onboarding_time": "fast"
  },
  "weight_range_in_lbs": "100-120",
  "return_needed": "false"
}
```

**Response**:
```json
{
    "coverage_area_filtered_vendors": [
        "UPS",
        "FedEx",
        "USPS",
        "DHL Express",
        "OnTrac",
        ...
    ],
    "carrier_attributes_evaluated_vendors": [
        {
            "UPS": 0.9
        },
        {
            "FedEx": 0.8
        },
        ...
    ],
    "weight_range_in_lbs_analyzed_vendors_": [
        {
            "UPS": 1.0
        },
        {
            "FedEx": 1.0
        },
        ...
    ],
    "return_needed_assessed_vendors": [
        {
            "UPS": 1.0
        },
        {
            "FedEx": 1.0
        },
        ...
    ],
    "ranked_vendors": [
        {
            "first_ranked_carrier": "UPS",
            "explanation": "UPS offers excellent coverage in both New York and California while ensuring fast onboarding and a high level of sustainability. Additionally, it can support the weight range of 100-120 lbs effectively."
        },
        ...
    ]
}
```

## Testing the API

You can test the API endpoints using tools like [Postman](https://www.postman.com/) or [cURL](https://curl.se/).

### Example cURL Command

To test the `POST /process-shipping/` endpoint, use the following cURL command:

```bash
curl -X POST "http://127.0.0.1:8000/process-shipping/" -H "Content-Type: application/json" -d '{
  "coverage_area": ["new york", "California"],
  "carrier_attributes": {
    "tracking": "none",
    "sustainability": "high",
    "onboarding_time": "fast"
  },
  "weight_range_in_lbs": "100-120",
  "return_needed": "false"
}'
```

### Expected Response

The response will contain the filtered and ranked shipping carriers based on the input criteria.

---

Feel free to reach out if you encounter any issues while setting up or running the server.
