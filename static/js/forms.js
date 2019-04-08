document.addEventListener("DOMContentLoaded", function(event) {
    document.querySelectorAll('.filter-tags .clean').forEach(function (elem, index) {
        elem.addEventListener('click', function (e) {
            e.preventDefault();
            this.parentNode.querySelector('input:checked').checked = false;                        
        });

    });
});