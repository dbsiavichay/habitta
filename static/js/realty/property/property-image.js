var inputImg = document.getElementById('image_input');

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

var uploadImage = function(base64image) {        
    var form = document.getElementById('image_form');
    document.getElementById('id_base64image').value = base64image;
    formData = getFormData(form);    

    $.ajax(form.action, {
        method: form.method,
        data: formData,
        processData: false,
        contentType: false,

        /*xhr: function () {
            var xhr = new XMLHttpRequest();

            xhr.upload.onprogress = function (e) {
                console.log(e);
                var percent = '0';
                var percentage = '0%';

                if (e.lengthComputable) {
                    percent = Math.round((e.loaded / e.total) * 100);
                    percentage = percent + '%';
                    //$progressBar.width(percentage).attr('aria-valuenow', percent).text(percentage);
                }
            };

            return xhr;
        },*/

        success: function (data) {            
            var galleryItem = document.querySelector('.gallery-item');
            var el = galleryItem.cloneNode(true);
            if (el.classList.contains('hidden')){
                el.classList.remove('hidden')
            }

            if (el.hasAttribute('style')){
                el.removeAttribute('style')
            }

            el.querySelector('img').src = data['image_url'];
            el.querySelector('a').href = data['image_url'];

            document.getElementById('gallery').appendChild(el);
            citybook.destroyLightGallery();
        },

        error: function (err) {
            console.log(err);
            //$alert.show().addClass('alert-warning').text('Upload error');
        },

        complete: function () {
            citybook.initLightGallery();
        },
    });
}


var createCropper = function (image) {
    var cropper = new Cropper(image, {
        aspectRatio: 16 / 9,
        autoCropArea:1,
        viewMode: 3,
        cropBoxResizable: false,
    });

    image.addEventListener('ready', function () {            
        var canvas = this.cropper.getCroppedCanvas({
            width: 800,
            height: 450,
        });

        uploadImage(canvas.toDataURL()); 
        this.cropper.destroy();           
    });
}

inputImg.addEventListener('change', function (e) {             
    var img = document.getElementById('cropper_image');           
    var files = e.target.files;
    var done = function (url) {        
        inputImg.value = '';
        img.src = url;
    };        

    if (files && files.length > 0) {
        var file = files[0];

        if (URL) {
            done(URL.createObjectURL(file));
        } else if (FileReader) {
            var reader = new FileReader();
            reader.onload = function (e) {
              done(reader.result);
            };
            reader.readAsDataURL(file);
        }
    }

    createCropper(img);    
}); 