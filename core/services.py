## operações externas ou serviços específicos, como chamadas de API, integração com terceiros, envio de notificações, etc.
import requests
import logging

logger = logging.getLogger(__name__)

def fetch_company_data(tax_id):
    """Consulta CNPJ em APIs públicas e retorna os dados formatados"""
    tax_id = tax_id.replace('.', '').replace('-', '').replace('/', '').strip()

    apis = [
        f"https://open.cnpja.com/office/{tax_id}",
        f"https://publica.cnpj.ws/cnpj/{tax_id}"
    ]

    for api_url in apis:
        try:
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data:
                return {
                    "full_name": (data.get('company', {}).get('name') or data.get('razao_social', "")).title(),
                    "preferred_name": (data.get('alias') or data.get('estabelecimento', {}).get('nome_fantasia', "")).title(),
                    "zip_code": data.get('address', {}).get('zip') or data.get('estabelecimento', {}).get('cep'),
                    "street": (data.get('address', {}).get('street') or f"{data.get('estabelecimento', {}).get('tipo_logradouro')} {data.get('estabelecimento', {}).get('logradouro')}").title(),
                    "number": data.get('address', {}).get('number') or data.get('estabelecimento', {}).get('numero'),
                    "neighborhood": (data.get('address', {}).get('district') or data.get('estabelecimento', {}).get('bairro', "")).title(),
                    "city": (data.get('address', {}).get('city') or data.get('estabelecimento', {}).get('cidade', {}).get('nome', "")).title(),
                    "state": data.get('address', {}).get('state') or data.get('estabelecimento', {}).get('estado', {}).get('sigla')
                }
        except requests.RequestException as e:
            logger.error(f"Erro ao consultar API {api_url}: {e}")

    return None