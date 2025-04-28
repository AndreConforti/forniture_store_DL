// Comportamentos dos botões de busca em CNPJ e CEP de acordo com o tipo de cliente
$(document).ready(function() {
    function toggleSearchButtons() {
        const customerType = $('.customer-type-select').val();
        $('#search-tax-id').prop('disabled', customerType !== 'CORP');
        $('#search-zip-code').prop('disabled', customerType !== 'IND');
    }

    toggleSearchButtons();
    $('.customer-type-select').change(toggleSearchButtons);
});
