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
                # Extrai a Inscrição Estadual (IE) ativa ou retorna ""
                state_registration = ""
                
                # API 1 (open.cnpja.com)
                if "registrations" in data:
                    active_registration = next(
                        (reg for reg in data.get("registrations", []) 
                         if reg.get("enabled") and reg.get("type", {}).get("text") == "IE Normal"),
                        None
                    )
                    if active_registration:
                        state_registration = active_registration.get("number", "")
                
                # API 2 (publica.cnpj.ws)
                elif "estabelecimento" in data:
                    active_registration = next(
                        (ie for ie in data.get("estabelecimento", {}).get("inscricoes_estaduais", []) 
                         if ie.get("ativo")),
                        None
                    )
                    if active_registration:
                        state_registration = active_registration.get("inscricao_estadual", "")

                return {
                    "full_name": (data.get('company', {}).get('name') or data.get('razao_social', "")).title(),
                    "preferred_name": (data.get('alias') or data.get('estabelecimento', {}).get('nome_fantasia', "")).title(),
                    "zip_code": data.get('address', {}).get('zip') or data.get('estabelecimento', {}).get('cep', ""),
                    "street": (data.get('address', {}).get('street') or 
                              f"{data.get('estabelecimento', {}).get('tipo_logradouro', '')} {data.get('estabelecimento', {}).get('logradouro', '')}").title().strip(),
                    "number": data.get('address', {}).get('number') or data.get('estabelecimento', {}).get('numero', ""),
                    "neighborhood": (data.get('address', {}).get('district') or data.get('estabelecimento', {}).get('bairro', "")).title(),
                    "city": (data.get('address', {}).get('city') or data.get('estabelecimento', {}).get('cidade', {}).get('nome', "")).title(),
                    "state": data.get('address', {}).get('state') or data.get('estabelecimento', {}).get('estado', {}).get('sigla', ""),
                    "state_registration": state_registration  
                }
        except requests.RequestException as e:
            logger.error(f"Erro ao consultar API {api_url}: {e}")

    return None


def fetch_address_data(zip_code):
    """Consulta CEP em APIs públicas e retorna os dados formatados"""
    zip_code = zip_code.replace('-', '').strip()
    
    apis = [
        f"https://viacep.com.br/ws/{zip_code}/json/",
        f"https://brasilapi.com.br/api/cep/v1/{zip_code}"
    ]

    for api_url in apis:
        try:
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data and "erro" not in data:
                return {
                    "zip_code": zip_code,
                    "street": data.get("logradouro", ""),
                    "neighborhood": data.get("bairro", ""),
                    "city": data.get("localidade", ""),
                    "state": data.get("uf", "")
                }
        except requests.RequestException as e:
            logger.error(f"Erro ao consultar API {api_url}: {e}")

    return None