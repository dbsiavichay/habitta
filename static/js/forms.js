var getFormData = function(form) {
    var formData = new FormData();
    var elements = form.querySelectorAll('input, select, textarea');
    for( var i = 0; i < elements.length; ++i ) {
        var element = elements[i];
        var name = element.name;
        var value = element.value;
        if (element.type=='file' && element.files)
            value = element.files[0]
        if(!name) continue;
        formData.append(name, value);        
    }
    return formData;
}

document.addEventListener("DOMContentLoaded", function(event) {
	//Clean radios
    document.querySelectorAll('.filter-tags .clean').forEach(function (elem, index) {
        elem.addEventListener('click', function (e) {
            e.preventDefault();
            this.parentNode.querySelector('input:checked').checked = false;                        
        });

    });
});