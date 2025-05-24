$(document).ready(function() {
    const supplierTypeSelect = $('.supplier-type-select'); // Usando a classe definida no HTML
    const taxIdInput = $('#{{ form.tax_id.id_for_label }}'); // Para pegar o ID dinamicamente se necessário, ou fixar como 'id_tax_id'
    const zipCodeInput = $('#{{ form.zip_code.id_for_label }}'); // ou 'id_zip_code'

    const searchTaxIdButton = $('#search-tax-id'); // ID do botão de busca CNPJ no HTML
    const searchZipCodeButton = $('#search-zip-code'); // ID do botão de busca CEP no HTML

    const stateRegFieldDiv = $('#state-registration-field-div'); // ID da div do campo IE
    const municipalRegFieldDiv = $('#municipal-registration-field-div'); // ID da div do campo IM

    // Função para controlar visibilidade dos campos fiscais (IE/IM) e habilitar/desabilitar botões
    function updateFormControls() {
        const selectedType = supplierTypeSelect.val();

        if (selectedType === 'CORP') {
            searchTaxIdButton.prop('disabled', false);
            searchZipCodeButton.prop('disabled', true); // CEP é mais para PF ou endereço manual PJ
            stateRegFieldDiv.show();
            municipalRegFieldDiv.show();
        } else if (selectedType === 'IND') {
            searchTaxIdButton.prop('disabled', true);
            searchZipCodeButton.prop('disabled', false);
            stateRegFieldDiv.hide();
            municipalRegFieldDiv.hide();
        } else { // Caso geral ou nenhum tipo selecionado
            searchTaxIdButton.prop('disabled', true);
            searchZipCodeButton.prop('disabled', true);
            stateRegFieldDiv.show(); // Ou hide() dependendo do default desejado
            municipalRegFieldDiv.show(); // Ou hide()
        }
    }

    // Inicializa e adiciona listener para mudança de tipo
    if (supplierTypeSelect.length) {
        updateFormControls(); // Chama na carga da página
        supplierTypeSelect.on('change', updateFormControls);
    }

    // Função para buscar CNPJ e preencher o formulário
    if (searchTaxIdButton.length) {
        searchTaxIdButton.click(function() {
            const taxIdValue = $('input[name="tax_id"]').val().replace(/\D/g, ''); // Pegar pelo name para mais robustez

            if (taxIdValue.length !== 14) {
                alert('Informe um CNPJ válido com 14 dígitos.');
                return;
            }

            $.ajax({
                url: "{% url 'suppliers:search_cnpj' %}", // Usando a tag de URL do Django
                type: 'GET',
                data: { tax_id: taxIdValue },
                dataType: 'json',
                success: function(data) {
                    if (data.error) {
                        alert('Erro: ' + data.error);
                    } else {
                        $('input[name="full_name"]').val(data.full_name || '');
                        $('input[name="preferred_name"]').val(data.preferred_name || '');
                        $('input[name="state_registration"]').val(data.state_registration || '');
                        // municipal_registration geralmente não vem da API

                        // Endereço (se a API retornar)
                        $('input[name="zip_code"]').val(data.zip_code || '').trigger('input'); // trigger input para máscaras
                        $('input[name="street"]').val(data.street || '');
                        $('input[name="number"]').val(data.number || '');
                        $('input[name="neighborhood"]').val(data.neighborhood || '');
                        $('input[name="city"]').val(data.city || '');
                        $('select[name="state"]').val(data.state || '').trigger('change'); // trigger change para selects estilizados

                        // Contato (se a API retornar)
                        if (data.phone) {
                             $('input[name="phone"]').val(data.phone.replace(/\D/g, '') || '').trigger('input');
                        }
                        if (data.email) {
                            $('input[name="email"]').val(data.email || '');
                        }
                        
                        alert('Dados do CNPJ preenchidos. Por favor, verifique e complete o cadastro.');
                        // Opcional: focar em um campo específico após o preenchimento
                        // $('input[name="contact_person"]').focus();
                    }
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    console.error("Erro AJAX CNPJ:", textStatus, errorThrown, jqXHR.responseText);
                    alert('Erro ao buscar dados do CNPJ. Verifique o console para mais detalhes.');
                }
            });
        });
    }

    // Função para buscar CEP e preencher o formulário
    if (searchZipCodeButton.length) {
        searchZipCodeButton.click(function() {
            const zipCodeValue = $('input[name="zip_code"]').val().replace(/\D/g, '');

            if (zipCodeValue.length !== 8) {
                alert('Informe um CEP válido com 8 dígitos.');
                return;
            }

            $.ajax({
                url: "{% url 'suppliers:search_zip_code' %}", // Usando a tag de URL do Django
                type: 'GET',
                data: { zip_code: zipCodeValue },
                dataType: 'json',
                success: function(data) {
                    if (data.error) {
                        alert('Erro: ' + data.error);
                    } else {
                        $('input[name="street"]').val(data.street || '');
                        $('input[name="neighborhood"]').val(data.neighborhood || '');
                        $('input[name="city"]').val(data.city || '');
                        $('select[name="state"]').val(data.state || '').trigger('change');
                        
                        alert('Dados do CEP preenchidos. Por favor, complete o endereço.');
                        $('input[name="number"]').focus(); // Focar no campo número
                    }
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    console.error("Erro AJAX CEP:", textStatus, errorThrown, jqXHR.responseText);
                    alert('Erro ao buscar dados do CEP. Verifique o console para mais detalhes.');
                }
            });
        });
    }

    // Aplicar máscaras (exemplo com jQuery Mask Plugin)
    // Certifique-se de que o jQuery Mask Plugin está incluído no seu base_home.html ou neste template
    if (typeof $.fn.mask === 'function') {
        $('input[name="zip_code"]').mask('00000-000');
        $('input[name="phone"]').mask('(00) 00000-0000');

        // Máscara dinâmica para CPF/CNPJ
        var taxIdField = $('input[name="tax_id"]');
        var taxIdOptions = {
            onKeyPress: function(taxId, e, field, options) {
                var masks = ['000.000.000-009', '00.000.000/0000-00'];
                var mask = (taxId.length > 14) ? masks[1] : masks[0];
                taxIdField.mask(mask, options);
            }
        };
        taxIdField.mask('000.000.000-009', taxIdOptions); // Inicia com máscara de CPF
        
        // Lógica adicional para limpar a máscara se o tipo de cliente mudar
        // e o campo já estiver preenchido, ou para aplicar a máscara correta na carga.
        // Isso pode ficar complexo rapidamente. Uma alternativa é não usar máscara para CPF/CNPJ
        // e confiar na entrada de "apenas números" + validação.
        // Ou, se o tipo de documento for definido antes, aplicar a máscara correspondente.
        // Ex: Se o `supplierTypeSelect` mudar, re-aplicar a máscara correta no taxIdField.
         supplierTypeSelect.on('change', function() {
            const currentTaxId = taxIdField.val().replace(/\D/g, '');
            if (supplierTypeSelect.val() === 'CORP') {
                taxIdField.unmask();
                taxIdField.mask('00.000.000/0000-00');
            } else {
                taxIdField.unmask();
                taxIdField.mask('000.000.000-009');
            }
            // Se havia valor, tentar reaplicar. Pode ser imperfeito.
            // taxIdField.val(currentTaxId).trigger('input'); 
        }).trigger('change'); // Trigger na carga para aplicar máscara inicial correta
    }
});