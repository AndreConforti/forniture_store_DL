document.addEventListener('DOMContentLoaded', function() {
    // Elementos globais
    const supplierTypeSelect = document.querySelector('.supplier-type-select');
    const searchTaxIdBtn = document.getElementById('search-tax-id');
    const searchZipCodeBtn = document.getElementById('search-zip-code');
    const stateRegistrationField = document.getElementById('state-registration-field');
    const municipalRegistrationField = document.getElementById('municipal-registration-field');
    const phoneField = document.getElementById('id_phone');
    
    // Máscaras (se estiver usando jQuery Mask)
    if (typeof $.fn.mask === 'function' && phoneField) {
        $(phoneField).mask('(00) 00000-0000');
    }

    // Funções de controle
    function toggleSearchButtons() {
        const supplierType = supplierTypeSelect ? supplierTypeSelect.value : 'CORP';
        if (searchTaxIdBtn) searchTaxIdBtn.disabled = supplierType !== 'CORP';
        if (searchZipCodeBtn) searchZipCodeBtn.disabled = supplierType !== 'IND';
    }

    function toggleFiscalFields() {
        const supplierType = supplierTypeSelect ? supplierTypeSelect.value : 'CORP';
        if (stateRegistrationField && municipalRegistrationField) {
            if (supplierType === 'CORP') {
                stateRegistrationField.style.display = 'block';
                municipalRegistrationField.style.display = 'block';
            } else {
                stateRegistrationField.style.display = 'none';
                municipalRegistrationField.style.display = 'none';
            }
        }
    }

    // Busca CNPJ
    function handleTaxIdSearch() {
        if (!searchTaxIdBtn) return;
        
        searchTaxIdBtn.addEventListener('click', function() {
            const taxId = document.getElementById('id_tax_id').value.replace(/\D/g, '');
            
            if (!taxId) {
                alert('Informe um CNPJ válido.');
                return;
            }

            fetch(`/suppliers/search-cnpj/?tax_id=${taxId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert(data.error);
                    } else {
                        if (data.full_name) document.getElementById('id_full_name').value = data.full_name;
                        if (data.preferred_name) document.getElementById('id_preferred_name').value = data.preferred_name;
                        if (data.state_registration) document.getElementById('id_state_registration').value = data.state_registration;
                        if (data.zip_code) document.getElementById('id_zip_code').value = data.zip_code;
                        if (data.street) document.getElementById('id_street').value = data.street;
                        if (data.number) document.getElementById('id_number').value = data.number;
                        if (data.neighborhood) document.getElementById('id_neighborhood').value = data.neighborhood;
                        if (data.city) document.getElementById('id_city').value = data.city;
                        if (data.state) document.getElementById('id_state').value = data.state;
                    }
                })
                .catch(() => {
                    alert('Erro ao buscar dados do CNPJ. Tente novamente.');
                });
        });
    }

    // Busca CEP
    function handleZipCodeSearch() {
        if (!searchZipCodeBtn) return;
        
        searchZipCodeBtn.addEventListener('click', function() {
            const zipCode = document.getElementById('id_zip_code').value.replace(/\D/g, '');
            
            if (!zipCode || zipCode.length < 8) {
                alert('Informe um CEP válido.');
                return;
            }

            fetch(`/suppliers/search-zip-code/?zip_code=${zipCode}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert(data.error);
                    } else {
                        if (data.street) document.getElementById('id_street').value = data.street;
                        if (data.neighborhood) document.getElementById('id_neighborhood').value = data.neighborhood;
                        if (data.city) document.getElementById('id_city').value = data.city;
                        if (data.state) document.getElementById('id_state').value = data.state;
                    }
                })
                .catch(() => {
                    alert('Erro ao buscar dados do CEP.');
                });
        });
    }

    // Event Listeners
    if (supplierTypeSelect) {
        supplierTypeSelect.addEventListener('change', function() {
            toggleSearchButtons();
            toggleFiscalFields();
        });
    }

    // Inicialização
    toggleSearchButtons();
    toggleFiscalFields();
    handleTaxIdSearch();
    handleZipCodeSearch();

    // jQuery (se necessário para máscaras)
    if (typeof $ !== 'undefined') {
        $(document).ready(function() {
            // Máscaras adicionais se necessário
            $('#id_zip_code').mask('00000-000');
        });
    }
});