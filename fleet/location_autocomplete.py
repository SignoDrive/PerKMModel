import requests
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def autocomplete_location(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method allowed'}, status=405)

    query = request.GET.get('query', '').strip()
    if not query or len(query) < 3:
        return JsonResponse({'suggestions': []})

    api_key = os.getenv('OLA_MAPS_API_KEY') or getattr(settings, "OLA_MAPS_API_KEY", None)
    if not api_key:
        return JsonResponse({'error': 'Ola Maps API key not configured'}, status=500)

    try:
        url = f"https://api.olamaps.io/places/v1/autocomplete"
        params = {'input': query, 'api_key': api_key, 'language': 'en'}
        headers = {'X-Request-Id': f'autocomplete_{query[:20]}_{hash(query) % 10000}'}

        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code != 200:
            return JsonResponse({'error': f'Autocomplete API error: {response.status_code}'}, status=400)

        data = response.json()
        suggestions = []

        if data.get('predictions'):
            for prediction in data['predictions'][:5]:
                suggestions.append({
                    'place_id': prediction.get('place_id'),
                    'description': prediction.get('description'),
                    'structured_formatting': prediction.get('structured_formatting', {})
                })

        return JsonResponse({'suggestions': suggestions})

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Network error: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Autocomplete error: {str(e)}'}, status=500)
