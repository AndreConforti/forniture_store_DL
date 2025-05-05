document.addEventListener('DOMContentLoaded', function() {
    // Busca CNPJ
    document.getElementById('search-tax-id').addEventListener('click', function() {
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
                    document.getElementById('id_full_name').value = data.full_name;
                    document.getElementById('id_preferred_name').value = data.preferred_name;
                    document.getElementById('id_state_registration').value = data.state_registration;
                    document.getElementById('id_zip_code').value = data.zip_code;
                    document.getElementById('id_street').value = data.street;
                    document.getElementById('id_number').value = data.number;
                    document.getElementById('id_neighborhood').value = data.neighborhood;
                    document.getElementById('id_city').value = data.city;
                    document.getElementById('id_state').value = data.state;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Erro ao buscar dados do CNPJ');
            });
    });

    // Busca CEP
    document.getElementById('search-zip-code').addEventListener('click', function() {
        const zipCode = document.getElementById('id_zip_code').value.replace(/\D/g, '');
        
        if (!zipCode || zipCode.length < 8) {
            alert('Informe um CEP válido com 8 dígitos.');
            return;
        }

        fetch(`/suppliers/search-zip-code/?zip_code=${zipCode}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    document.getElementById('id_street').value = data.street;
                    document.getElementById('id_neighborhood').value = data.neighborhood;
                    document.getElementById('id_city').value = data.city;
                    document.getElementById('id_state').value = data.state;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Erro ao buscar dados do CEP');
            });
    });
});