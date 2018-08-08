 var getFormData = function(form) {
    var formData = new FormData();
    var elements = form.querySelectorAll('input, select, textarea');
    for( var i = 0; i < elements.length; ++i ) {
        var element = elements[i];
        var name = element.name;
        var value = element.value;

        if(name) {
            formData.append(name, value);
        }
    }

    return formData;
}