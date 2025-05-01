// document.addEventListener('DOMContentLoaded', function() {
//     // Inicializa todos os submenus com display: none
//     document.querySelectorAll('.has-submenu ul.collapse').forEach(submenu => {
//         submenu.style.display = 'none';
//     });
    
//     // Abre automaticamente submenus com itens ativos
//     document.querySelectorAll('.has-submenu').forEach(item => {
//         const submenu = item.querySelector('ul');
//         const toggle = item.querySelector('.nav-link');
        
//         if (submenu.querySelector('.active')) {
//             // Usamos setTimeout para garantir que o display: none seja aplicado primeiro
//             setTimeout(() => {
//                 new bootstrap.Collapse(submenu, { toggle: false }).show();
//                 toggle.classList.add('active-parent');
//             }, 10);
//         }
//     });
    
//     // Configura os eventos de colapso
//     document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(toggle => {
//         const target = document.querySelector(toggle.getAttribute('data-bs-target'));
        
//         toggle.addEventListener('click', function(e) {
//             e.preventDefault();
            
//             // Garante que o display está none antes de animar
//             target.style.display = 'none';
            
//             // Inicia a animação
//             const bsCollapse = new bootstrap.Collapse(target, { toggle: true });
//         });
//     });
// });