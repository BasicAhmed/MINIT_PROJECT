import requests
import time

token_cache = {
    "access_token": None,
    "expires_at": 0
}

def get_access_token(client_id, client_secret):
    if token_cache['access_token'] and time.time() < token_cache['expires_at']:
        return token_cache['access_token']

    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        token_cache['access_token'] = token_data.get('access_token')
        token_cache['expires_at'] = time.time() + token_data.get('expires_in', 0) - 60
        return token_cache['access_token']
    else:
        raise Exception(f"Failed to authenticate: {response.status_code}, {response.text}")

def get_flights(origin, destination, passengers, date, access_token):
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": date,
        "adults": passengers,
        "nonStop": "false",
        "max": "4"
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch flights: {response.status_code}, {response.text}")

def extract_flight_details(flights_data, max_results=5):
    flight_details = []
    for offer in flights_data.get("data", [])[:max_results]:
        price_details = offer.get("price", {})
        total_price = price_details.get("total")
        for segment in offer["itineraries"][0]["segments"]:
            flight_details.append({
                "flight_number": segment["carrierCode"] + segment["number"],
                "airline": segment["operating"]["carrierCode"],
                "departure_time": segment["departure"]["at"],
                "arrival_time": segment["arrival"]["at"],
                "price": f"{round((float(total_price)*4.67), 2)}" if total_price else "N/A"
            })
    return flight_details