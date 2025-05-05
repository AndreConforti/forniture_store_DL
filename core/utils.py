from core.services import fetch_company_data, fetch_address_data
from django.http import JsonResponse


def fetch_company_data_view(request):
    """Endpoint para buscar dados da empresa via CNPJ"""
    tax_id = request.GET.get('tax_id', '').replace('.', '').replace('-', '').replace('/', '').strip()

    if not tax_id:
        return JsonResponse({'error': 'CNPJ não informado'}, status=400)

    data = fetch_company_data(tax_id)
    if data:
        return JsonResponse(data)

    return JsonResponse({'error': 'Não foi possível obter os dados'}, status=500)


def fetch_address_data_view(request):
    """Endpoint para buscar dados do CEP"""
    zip_code = request.GET.get('zip_code', '').strip()

    if not zip_code:
        return JsonResponse({'error': 'CEP não informado'}, status=400)

    data = fetch_address_data(zip_code)
    if data:
        return JsonResponse(data)

    return JsonResponse({'error': 'Não foi possível obter os dados'}, status=500)
